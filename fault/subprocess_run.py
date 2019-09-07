import logging
import shlex
from subprocess import Popen, PIPE, CompletedProcess
from fault.user_cfg import FaultConfig


# Terminal formatting codes
MAGENTA = '\x1b[35m'
CYAN = '\x1b[36m'
BRIGHT = '\x1b[1m'
RESET_ALL = '\x1b[0m'


def display_line(line, disp_type):
    # generic function to display a line using various
    # methods.

    # then display the line using the desired method
    if disp_type is None:
        pass
    elif disp_type == 'print':
        print(line)
    elif disp_type == 'info':
        logging.info(line.rstrip())
    elif disp_type == 'warn':
        logging.warning(line.rstrip())
    else:
        raise Exception(f'Invalid log_type: {disp_type}.')


def process_output(fd, disp_type, name):
    # generic line-processing function to display lines
    # as they are produced as output in and check for errors.

    retval = ''
    any_line = False
    for line in fd:
        # Add line to value to be returned
        retval += line

        # Display opening text if needed
        if not any_line:
            any_line = True
            display_line(MAGENTA + BRIGHT + f'<{name}>' + RESET_ALL,
                         disp_type=disp_type)

        # display if desired
        display_line(line=line.rstrip(), disp_type=disp_type)

    # Display closing text if needed
    if any_line:
        display_line(MAGENTA + BRIGHT + f'</{name}>' + RESET_ALL,
                     disp_type=disp_type)

    # Return the full output contents for further processing
    return retval


def subprocess_run(args, cwd=None, env=None, disp_type='print', err_str=None,
                   chk_ret_code=True, shell=False, plain_logging=True,
                   use_fault_cfg=True):
    # "Deluxe" version of subprocess.run that can display STDOUT lines as they
    # come in, looks for errors in STDOUT and STDERR (raising an exception if
    # one is found), and can check the return code from the subprocess
    # (raising an exception if non-zero).
    #
    # The return value is a CompletedProcess, which has properties
    # "returncode", "stdout", and "stderr".  This allows for further processing
    # of the results if desired.
    #
    # Note that only STDOUT is displayed in realtime; STDERR is displayed in
    # its entirety after the subprocess runs.  This is mainly to avoid the
    # confusion that arises when interleaving STDOUT and STDERR.
    #
    # args: List of arguments, with the same meaning as subprocess.run.
    #       Unlike subprocess.run, however, this should always be a list.
    # cwd: Directory in which to run the subprocess.
    # env: Dictionary representing the environment variables to be set
    #      while running the subprocess.  In None, defaults are determined
    #      based on one of the optional fault user config files.
    # disp_type: None, 'print', 'info', or 'warn'.  If None, don't display
    #            anything while running the subprocess.  If 'print', use
    #            the Python 'print' command to display output.  If 'info',
    #            using logging.info, and if 'warn', use logging.warning.
    # err_str: If not None, look for err_str in each line of STDOUT and
    #          STDERR, raising an AssertionError if it is found.
    # chk_ret_code: If True, check the return code after the subprocess runs,
    #               raising an AssertionError if it is non-zero.
    # shell: If True, shell-quote arguments and concatenate using spaces into
    #        a string, then Popen with shell=True.  This is sometimes needed
    #        when running programs if they are actually scripts (e.g.,
    #        Verilator)
    # plain_logging: If True (default), use plain output formatting for
    #                all logging.  This is recommended since it makes
    #                it easier to read the many lines of output produced
    #                by typical suprocess calls.
    # use_fault_cfg: If True (default) and env is None, then use FaultConfig
    #                to fill in default environment variables.

    # set defaults
    if env is None and use_fault_cfg:
        env = FaultConfig().get_sim_env()

    # temporarily use plain formatting for all logging handlers.  this
    # makes the output cleaner and more readable -- otherwise the
    # output lines would all be prepended with the debug level,
    # line number, etc.
    if plain_logging:
        orig_fmts = []
        handlers = logging.getLogger().handlers
        plain_fmt = logging.Formatter()
        for handler in handlers:
            orig_fmts.append(handler.formatter)
            handler.setFormatter(plain_fmt)

    # print out the command in a format that can be copy-pasted
    # directly into a terminal (i.e., with proper quoting of arguments)
    cmd_str = ' '.join(shlex.quote(arg) for arg in args)
    display_line(CYAN + BRIGHT + 'Running command: ' + RESET_ALL + cmd_str,
                 disp_type=disp_type)

    # combine arguments into a string if needed for shell=True
    if shell:
        args = cmd_str

    # run the subprocess
    with Popen(args, cwd=cwd, env=env, stdout=PIPE, stderr=PIPE, bufsize=1,
               universal_newlines=True, shell=shell) as p:

        # print out STDOUT, then STDERR
        # threads could be used here but pytest does not detect exceptions
        # in child threads, so for now the outputs are printed sequentially
        stdout = process_output(fd=p.stdout, disp_type=disp_type,
                                name='STDOUT')
        stderr = process_output(fd=p.stderr, disp_type=disp_type,
                                name='STDERR')

        # get return code and check result if desired
        returncode = p.wait()
        if chk_ret_code:
            assert not returncode, f'Got non-zero return code: {returncode}.'

        # look for errors in STDOUT or STDERR
        if err_str is not None:
            assert err_str not in stdout, f'Found "{err_str}" in STDOUT.'  # noqa
            assert err_str not in stderr, f'Found "{err_str}" in STDERR.'  # noqa

        # return a completed process object containing the results
        retval = CompletedProcess(args=args, returncode=returncode,
                                  stdout=stdout, stderr=stderr)

    # go back to using the original formatters for each logging handler
    if plain_logging:
        for handler, fmt in zip(handlers, orig_fmts):
            handler.setFormatter(fmt)

    # return the output from the subprocess
    return retval
