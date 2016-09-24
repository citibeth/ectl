from __future__ import print_function
import io
import re
import os
import sys

class Line(object):
    __slots__ = ['source', 'source_lineno', 'lineno', 'isection', \
        'divider', 'raw', 'parsed', 'param']
    def __init__(self, source, source_lineno, raw):
        self.source = source
        self.source_lineno = source_lineno
        self.lineno = None
        self.isection = None
        self.divider = False
        self.raw = raw
        self.parsed = None        # Parsed version of this line
        self.param = None        # Higher-level Param object this line was used to set

    def remove_comments(self):
        """Returns the line, stripped of comments"""

        line = self.raw

        # Remove Fortran-style comments
        exp = line.find('!')
        if (exp >= 0): line = line[:exp]

        # Remove C-style comments too
        # http://stackoverflow.com/questions/2319019/using-regex-to-remove-comments-from-source-files
        line = re.sub(re.compile('/\*.*?\*/',re.DOTALL ) ,'' ,line)

        line = line.strip()
        return line

    def __repr__(self):
        return repr(self.raw)

    def __str__(self):
        return '(%s, %s): %s' % (self.source, self.lineno, self.raws[-1])

def find_in_path(fname, search_path):
    for path in search_path:
        candidate = os.path.join(path, fname)
        if os.path.exists(candidate):
            return candidate
    raise ValueError('File not found in path: %s' % fname)

includeRE = re.compile('\s*#include\s*"(.*?)"\s*(!\s*)?')

def preprocessor(fname, search_path):
    """Load a fully preprocessed rundeck from the templates directory.
    Works as a generator, producing one line at a time."""
    try:
        with open(fname, 'r') as fin:
            source_lineno = 0
            while True:
                line = next(fin)
                match = includeRE.match(line)
                if match is None:
                    yield Line(fname, source_lineno, line)
                    source_lineno += 1
                else:
                    leaf1 = match.group(1).decode()
                    fname1 = find_in_path(leaf1, search_path)
                    yield Line(fname, source_lineno, '! ---------- BEGIN #include %s\n' % fname1.encode())
                    for line in preprocessor(fname1, search_path):
                        yield line
                    yield Line(fname, source_lineno, '! ---------- END #include %s\n' % fname1.encode())
    except EOFError:
        pass


sectionRE = re.compile(r'\s*((Preamble):?|(Preprocessor\s+Options):?|(Run\s+Options):?|(Object\s+modules):?|(Components):?|(Component\s+Options):?|(Data\s+input\s+files):?|(&&PARAMETERS)|(&INPUTZ))\s*')
num_sections = 9

def sectionalize(fin):
    """Attach global line number..."""
    isection = 0        # Current section
    lineno=1

    try:
        while True:
            line = next(fin)

            # Determine section we're in
            match = sectionRE.match(line.raw)
            if match is None:
                line.isection = isection
            else:
                groups = match.groups()[1:]     # Skip the top-level group
                isection = 0
                while True:
                    if groups[isection] is not None:
                        break
                    isection += 1
                    if isection == len(groups):                        
                        raise ValueError('Could not find next section for "%s"' % line.raw)
                line.isection = isection            # Section separator
                line.divider = True

            # Attach line number
            line.lineno = lineno
            lineno += 1

            yield line
    except StopIteration:
        return

# =======================================================================


# ----------------------------------------------------------
# Parsers for the different sections
# Must return parsed-line.  None if line is to be disregarded
class Parser(object):
    pass


class CopyLines(Parser):
    def __call__(self, line):
        return line


preprocessorRE = re.compile(r'\s*#define\s+([^\s]*)(\s+(.*))?')
class PreprocessorOptions(Parser):
    def __call__(self, line):
        unparsed = line.remove_comments()

        match = preprocessorRE.match(unparsed)
        if match is not None:
            return match.group(1), match.group(3)
        else:
            return None

key_eq_valueRE = re.compile(r'\s*([^=\s]*)\s*=\s*([^!]*).*')
class KeyEqValue(Parser):
    def __call__(self, line):
        unparsed = line.remove_comments()

        match = key_eq_valueRE.match(unparsed)
        if match is not None:
            return match.group(1), match.group(2).strip()
        else:
            return None

class ComponentOptions(Parser):
    def __call__(self, line):
        unparsed = line.remove_comments()

        match = key_eq_valueRE.match(unparsed)
        if match is not None:
            scomp = match.group(1)
            options = match.group(2).strip()
            parsed_options = []

            if scomp.startswith('OPTS_'):
                component = scomp[5:]
            else:
                component = scomp

            for opt in options.split(' '):
                if len(opt) == 0: continue
                words = opt.split('=')
                if len(words) != 2:
                    raise ValueError('Bad component option {0}'.format(opt))
                parsed_options.append((words[0].strip(), words[1].strip()))

            return component, parsed_options

class NameList(Parser):
    def __call__(self, line):
        unparsed = line.remove_comments()

        eqs = unparsed.split('=')
        eqs2 = []
        for x in eqs:
            comma = x.rfind(',')
            if (comma < 0):
                eqs2.append((x,))
            else:
                eqs2.append((x[:comma], x[comma+1:]))

        eqs3 = list()
        for i in range(0,len(eqs)-1):
            eqs3.append((eqs2[i][-1].strip(), eqs2[i+1][0].strip()))
        return eqs3

class InputZ(Parser):
    def __call__(self, line):
        unparsed = line.remove_comments()

        for ll in unparsed.split(','):
            match = key_eq_valueRE.match(ll)
            if match is not None:
                return match.group(1), match.group(2).strip()
            return None

class WordList(Parser):
    def __call__(self, line):
        unparsed = line.remove_comments()

        ret = list()
        words = unparsed.split(' ')
        for word in words:
            word = word.strip()
            if len(word) > 0: ret.append(word)
        if len(ret) > 0:
            return ret
        else:
            return None
# ----------------------------------------------------------
class Section(list):
    def __init__(self, isection, name):
        self.isection = isection
        self.name = name

    def parsed_lines(self):
        for line in self:
            if line.parsed is not None:
                yield line

class LegacyRundeck(object):
    def __init__(self, fin):
        self.lines = list()        # Raw lines in the rundeck

        section_parsers = [
            ('preamble', CopyLines()),
            ('Preprocessor Options', PreprocessorOptions()),
            ('Run Options', KeyEqValue()),
            ('Object Modules', WordList()),
            ('Components', WordList()),
            ('Component Options', ComponentOptions()),
            ('Data input files', KeyEqValue()),
            ('Parameters', KeyEqValue()),
            ('InputZ', NameList())
        ]

        # Initialize sections
        self.sections_list = list()
        self.sections = dict()
        for isection,(name,parser) in enumerate(section_parsers):
            section = Section(isection, name)  # list with a name
            self.sections_list.append(section)
            self.sections[name] = section

        # Fill in the sections
        fin = sectionalize(fin)
        for line in fin:
            if line.divider:
                line_tuple = (line, None)
            else:
                parser = section_parsers[line.isection][1]
                line.parsed = parser(line)
            self.lines.append(line)
            self.sections_list[line.isection].append(line)


    def __repr__(self):
        out = list()

        for line in self.lines:
            section = self.sections_list[line.isection]
            out.append(repr((line.lineno, line.isection, line.parsed or line.raw)))

#        for title,section in self.sections_list:
#            out.append(('---------------- %s' % title))
#            for line,parsed in section:
#                parsed = parsed or line.raw
#                out.append(repr((line.lineno, line.isection, parsed)))

        return '\n'.join(out)

