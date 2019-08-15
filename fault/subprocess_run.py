import logging
import subprocess


def display_subprocess_output(result):
    # display both standard output and standard error as INFO, since
    # since some useful debugging info is included in standard error

    to_display = {
        'STDOUT': result.stdout.decode(),
        'STDERR': result.stderr.decode()
    }

    for name, val in to_display.items():
        if val != '':
            logging.info(f'*** {name} ***')
            logging.info(val)


def subprocess_run(args, cwd, env, display=True):
    # Runs a subprocess in the user-specified directory with
    # the user-specified environment.

    logging.info(f"Running command: {' '.join(args)}")
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True)

    if display:
        display_subprocess_output(result)

    return result
