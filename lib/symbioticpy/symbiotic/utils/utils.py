#/usr/bin/python

import sys
from time import time

COLORS = {
    'RED'   : '\033[1;31m',
    'GREEN' : '\033[1;32m',
    'BROWN' : '\033[0;33m',
    'RESET' : '\033[0m'
}

def print_stream(msg, stream, prefix = None, print_nl = True, color = None):
    """
    Print message to stderr/stdout

    @ msg      : str    message to print
    @ prefix   : str    prefix for the message
    @ print_nl : bool  print new line after the message
    @ color    : str    color to use when printing, default None
    """

    # don't print color when the output is redirected
    # to a file
    if not stream.isatty():
        color = None

    if not color is None:
        stream.write(COLORS[color])

    if msg == '':
        return
    if not prefix is None:
        stream.write(prefix)

    stream.write(msg)

    if not color is None:
        stream.write(COLORS['RESET'])

    if print_nl:
        stream.write('\n')

    stream.flush()

def print_stderr(msg, prefix = None, print_nl = True, color = None):
    print_stream(msg, sys.stderr, prefix, print_nl, color)

def print_stdout(msg, prefix = None, print_nl = True, color = None):
    print_stream(msg, sys.stdout, prefix, print_nl, color)

def err(msg, color = 'RED'):
    print_stderr(msg, 'ERROR: ', color=color)
    sys.exit(1)

enable_debug = False
debug_opts = []
def enable_debug(d_opts):
    global enable_debug
    global debug_opts

    enable_debug = True
    debug_opts = d_opts

def dbg(msg, domain = 'all', print_nl = True):
    global enable_debug
    if enable_debug:
        global debug_opts
        if domain == 'all' or domain in debug_opts:
            print_stderr(msg, 'DBG: ', print_nl)

# variable used to measure elapsed time
last_time = None

def restart_counting_time():
    global last_time
    last_time = time()

def print_elapsed_time(msg):
    global last_time
    assert last_time is not None

    tm = time() - last_time
    print('{0}: {1}'.format(msg, tm))
    # set new starting point
    last_time = time()
