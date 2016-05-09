from __future__ import print_function
import io
import re
import os
import sys

def find_in_path(fname, search_path):
    for path in search_path:
        candidate = os.path.join(path, fname)
        if os.path.exists(candidate):
            return candidate
    raise ValueError('File not found in path: %s' % fname)

includeRE = re.compile(b'\s*#include\s*"(.*?)"\s*(!\s*)?')

def preprocessor(fname, search_path):
    """Load a fully preprocessed rundeck from the templates directory.
    Works as a generator, producing one line at a time."""
    try:
        with open(fname, 'rb') as fin:
            lineno = 1
            while True:
                line = next(fin)
                match = includeRE.match(line)
                if match is None:
                    yield (lineno, line)
                    lineno += 1
                else:
                    leaf1 = match.group(1).decode()
                    fname1 = find_in_path(leaf1, search_path)
                    yield (lineno, '! ---------- BEGIN #include %s\n' % fname1.encode())
                    for line_tuple in preprocessor(fname1, search_path):
                        yield line_tuple
                    yield (lineno, '! ---------- END #include %s\n' % fname1.encode())
    except EOFError:
        pass

# -------------------------------------------------------------------------
def iterable_to_stream(iterable, buffer_size=io.DEFAULT_BUFFER_SIZE):
    """
    Lets you use an iterable (e.g. a generator) that yields bytestrings as a read-only
    input stream.

    The stream implements Python 3's newer I/O API (available in Python 2's io module).
    For efficiency, the stream is buffered.

    See: http://stackoverflow.com/questions/6657820/python-convert-an-iterable-to-a-stream
    """
    class IterStream(io.RawIOBase):
        def __init__(self):
            self.leftover = None
        def readable(self):
            return True
        def readinto(self, b):
            try:
                l = len(b)  # We're supposed to return at most this much
                chunk = self.leftover or next(iterable)
                output, self.leftover = chunk[:l], chunk[l:]
                b[:len(output)] = output
                return len(output)
            except StopIteration:
                return 0    # indicate EOF
    return io.BufferedReader(IterStream(), buffer_size=buffer_size)

# =====================================================================
# ----------------------------------------------------------

# Finds the division between preprocessor sections
sectionRE = re.compile(r'\s*((Preamble:?)|(Preprocessor\s+Options:?)|(Run\s+Options:?)|(Object\s+modules:?)|(Components:?)|(Component\s+Options:?)|(Data\s+input\s+files:?)|(&&PARAMETERS)|(&INPUTZ))\s*')
num_sections = 9

def parse_section(fin, parse_line):
    """Rundecks are grouped in sections.  This parses the current section, and
    reports the section type of the next section."""
    while True:
        next_fin = next(fin)
        lineno, line = next_fin
        match = sectionRE.match(line)
        if match is None:
            parse_line(lineno, line)
        else:
            groups = match.groups()[1:]     # Skip the top-level group
            for i in range(0,len(groups)):
                if groups[i] is not None:
                    return i        # Next section
            raise ValueError('Could not find next section for ' + line)
# ----------------------------------------------------------
def remove_comments(line):
    # Remove Fortran-style comments
    exp = line.find('!')
    if (exp >= 0): line = line[:exp]

    # Remove C-style comments too
    # http://stackoverflow.com/questions/2319019/using-regex-to-remove-comments-from-source-files
    line = re.sub(re.compile("/\*.*?\*/",re.DOTALL ) ,"" ,line)

    line = line.strip()
    return line

# ----------------------------------------------------------
# Parsers for the different sections
class Parser(object):
    def __init__(self):
        self.section = list()

class CopyLines(Parser):
    def __call__(self, lineno, line):
        self.section.append(line)

class CopyLinesNoComments(Parser):
    def __call__(self, lineno, line):
        line = remove_comments(line)
        if len(line) > 0:
            self.section.append(line)



preprocessorRE = re.compile(r'\s*#define\s+([^\s]*)(\s+(.*))?')
class PreprocessorOptions(Parser):
    def __call__(self, lineno, line):
        line = remove_comments(line)

        match = preprocessorRE.match(line)
        if match is not None:
            self.section.append((match.group(1), match.group(3), (lineno, line)))

key_eq_valueRE = re.compile(r'\s*([^=\s]*)\s*=\s*([^!]*).*')
class KeyEqValue(Parser):
    def __call__(self, lineno, raw_line):
        line = remove_comments(raw_line)

        match = key_eq_valueRE.match(line)
        if match is not None:
            self.section.append((match.group(1), match.group(2).strip(), (lineno, raw_line)))

class ComponentOptions(Parser):
    def __call__(self, lineno, line):
        line = remove_comments(line)

        match = key_eq_valueRE.match(line)
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
                    raise ValueError('Bad component option {}'.format(opt))
                parsed_options.append((words[0].strip(), words[1].strip()))
            self.section.append((component, tuple(parsed_options), (lineno, line)))

class NameList(Parser):
    def __call__(self, lineno, line):
        line = remove_comments(line)

        eqs = line.split('=')
        eqs2 = []
        for x in eqs:
            comma = x.rfind(',')
            if (comma < 0):
                eqs2.append((x,))
            else:
                eqs2.append((x[:comma], x[comma+1:]))

        eqs3 = list()
        for i in range(0,len(eqs)-1):
            self.section.append((eqs2[i][-1].strip(), eqs2[i+1][0].strip()))

class InputZ(Parser):
    def __call__(self, lineno, line):
        line = remove_comments(line)

        for ll in line.split(','):
            match = key_eq_valueRE.match(ll)
            if match is not None:
                self.section.append((match.group(1), match.group(2).strip()))

class WordList(Parser):
    def __call__(self, lineno, line):
        line = remove_comments(line)

        words = line.split(' ')
        for word in words:
            word = word.strip()
            if len(word) > 0: self.section.append(word)
# ----------------------------------------------------------
class LegacyRundeck(dict):
    def __repr__(self):
        out = list()

        for title,values in self.items():
            out.append(('---------------- %s' % title))
            out.append(repr(values))

        return '\n'.join(out)


def read_rundeck(fin):
    """fin:
        Line generator producing the legacy rundeck."""
    buf = []
    section = 0

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

    while True:
        try:
            section = parse_section(fin, section_parsers[section][1])
        except StopIteration:
            break

    ret = LegacyRundeck()
    for parser in section_parsers:
        ret[parser[0]] = parser[1].section
    return ret

