import ectl
import ectl.launch
from ectl import iso8601, gissdate
import os
import datetime

description = 'Restarts a run from a restart file'

def setup_parser(subparser):
    ectl.launch.setup_parser(subparser)

    subparser.add_argument('--from', action='store', dest='restart_date',
        help='[iso8601] Date of restart file')


def find_rsf(dir, dt):
    """Find restart file for a particular date."""
    for file in os.listdir(dir):
        match = gissdate.dateRE.search(file)
        if match is not None:
            day = int(match.group(1))
            month = gissdate.str_to_month(match.group(2))
            year = int(match.group(3))

            dt2 = datetime.date(year, month, day)
            if (dt2 == dt):
                return os.path.join(dir, file)

    raise ValueError('No matchin rsf file for date {0}'.format(dt))

def restart(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    # Find restart file that matches the date
    if args.restart_date is None:
        rsf = None
    else:
        restart_date = iso8601.parse_date(args.restart_date)
        run = os.path.abspath(args.run)
        rsf = find_rsf(run, restart_date)

    ectl.launch.run(args, cmd='restart', rsf=rsf)
