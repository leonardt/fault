import logging
import shlex
from subprocess import Popen, PIPE, CompletedProcess
from fault.user_cfg import FaultConfig


def display_line(line, disp_type):
    # generic function to display a line using various
    # methods.
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


def process_output(fd, err_str, disp_type, name):
    # generic line-processing function to display lines
    # as they are produced as output in and check for errors.
    retval = []
    any_line = False
    for line in fd:
        # Display opening text if needed
        if not any_line:
            any_line = True
            display_line(f'*** Start {name} ***', disp_type=disp_type)
        # strip whitespace at end (including newline)
        line = line.rstrip()
        # display if desired
        display_line(line=line, disp_type=disp_type)
        # check for error
        if err_str is not None:
            assert err_str not in line, f'Found error in {name}: {line}'  # noqa
        # add line to the queue of outputs
        retval.append(line)
    # Display closing text if needed
    if any_line:
        display_line(f'*** End {name} ***', disp_type=disp_type)
    # Return the full output contents for further processing
    return '\n'.join(retval)


def subprocess_run(args, cwd, env=None, disp_type='info', err_str=None,
                   chk_ret_code=True):
    # Runs a subprocess while (optionally) displaying output
    # and processing lines as they come in.

    # set defaults
    env = env if env is not None else FaultConfig().get_sim_env()

    # print out the command in a format that can be copy-pasted
    # directly into a terminal (i.e., with proper quoting of arguments)
    cmd_str = ' '.join(shlex.quote(arg) for arg in args)
    logging.info(f"Running command: {cmd_str}")

    with Popen(args, cwd=cwd, env=env, stdout=PIPE, stderr=PIPE, bufsize=1,
               universal_newlines=True) as p:
        # process STDOUT, then STDERR
        # threads could be used here but pytest does not detect exceptions
        # in child threads, so for now the outputs are processed sequentially
        stdout = process_output(fd=p.stdout, err_str=err_str,
                                disp_type=disp_type, name='STDOUT')
        stderr = process_output(fd=p.stdout, err_str=err_str,
                                disp_type=disp_type, name='STDERR')

        # get return code and check result if desired
        returncode = p.wait()
        if chk_ret_code:
            assert not returncode, f'Got non-zero return code: {returncode}'

        # return a completed process object containing the results
        return CompletedProcess(args=args, returncode=returncode,
                                stdout=stdout, stderr=stderr)
