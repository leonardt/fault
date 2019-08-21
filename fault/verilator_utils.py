import shutil
import shlex
import subprocess


def bash_wrap(args):
    retval = []
    retval += ['bash']
    retval += ['-c']
    retval += [' '.join(shlex.quote(arg) for arg in args)]
    return retval


def verilator_version():
    # assemble the command
    cmd = [shutil.which('verilator'), '--version']
    cmd = bash_wrap(cmd)

    # run the command and parse out the version number
    version = subprocess.check_output(cmd)
    version = float(version.split()[1])

    # return version number
    return version


def verilator_comp_cmd(top=None, verilog_filename=None,
                       include_verilog_libraries=None,
                       include_directories=None,
                       driver_filename=None, verilator_flags=None):
    # set defaults
    if include_verilog_libraries is None:
        include_verilog_libraries = []
    if include_directories is None:
        include_directories = []
    if verilator_flags is None:
        verilator_flags = []

    # build up the command
    retval = []
    retval += [shutil.which('verilator')]
    retval += ['-Wall']
    retval += ['-Wno-INCABSPATH']
    retval += ['-Wno-DECLFILENAME']
    retval += verilator_flags
    if verilog_filename is not None:
        retval += ['--cc', f'{verilog_filename}']
    # -v arguments
    for file_ in include_verilog_libraries:
        retval += ['-v', f'{file_}']
    # -I arguments
    for dir_ in include_directories:
        retval += [f'-I{dir_}']
    if driver_filename is not None:
        retval += ['--exe', f'{driver_filename}']
    if top is not None:
        retval += ['--top-module', f'{top}']

    # return the command
    return bash_wrap(retval)


def verilator_make_cmd(top):
    cmd = []
    cmd += ['make']
    cmd += ['-C', 'obj_dir']
    cmd += ['-j']
    cmd += ['-f', f'V{top}.mk']
    cmd += [f'V{top}']
    return cmd
