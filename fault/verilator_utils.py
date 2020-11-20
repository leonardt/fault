from .subprocess_run import subprocess_run
import os


def verilator_version(disp_type='on_error'):
    # assemble the command
    cmd = ['verilator', '--version']

    # run the command and parse out the version number
    result = subprocess_run(cmd, shell=True, disp_type=disp_type)
    version = float(result.stdout.split()[1])

    # return version number
    return version


def verilator_comp_cmd(top=None, verilog_filename=None,
                       include_verilog_libraries=None,
                       include_directories=None,
                       driver_filename=None, verilator_flags=None,
                       coverage=False, use_kratos=False,
                       defines=None, parameters=None,
                       use_pysv=None):
    # set defaults
    if include_verilog_libraries is None:
        include_verilog_libraries = []
    if include_directories is None:
        include_directories = []
    if verilator_flags is None:
        verilator_flags = []
    if defines is None:
        defines = {}
    if parameters is None:
        parameters = {}

    # build up the command
    retval = []
    retval += ['verilator']
    retval += ['-Wall']
    retval += ['-Wno-INCABSPATH']
    retval += ['-Wno-DECLFILENAME']
    retval += verilator_flags

    if verilog_filename is not None:
        retval += ['--cc', f'{verilog_filename}']
        if use_kratos:
            from kratos_runtime import get_lib_path
            retval += [os.path.basename(get_lib_path())]
    if use_pysv:
        # this file name is the same cross all platforms
        retval += ["libpysv.so"]

    # -v arguments
    for file_ in include_verilog_libraries:
        retval += ['-v', f'{file_}']

    # -I arguments
    for dir_ in include_directories:
        retval += [f'-I{dir_}']

    # -D arguments
    for k, v in defines.items():
        if v is not None:
            retval += [f'-D{k}={v}']
        else:
            retval += [f'-D{k}']

    # -G arguments
    for k, v in parameters.items():
        retval += [f'-G{k}={v}']

    if driver_filename is not None:
        retval += ['--exe', f'{driver_filename}']
    if top is not None:
        retval += ['--top-module', f'{top}']

    # vpi flag
    if use_kratos:
        retval += ["--vpi"]
    if coverage:
        retval += ["--coverage"]

    # return the command
    return retval


def verilator_make_cmd(top):
    cmd = []
    cmd += ['make']
    cmd += ['-C', 'obj_dir']
    cmd += ['-j']
    cmd += ['-f', f'V{top}.mk']
    cmd += [f'V{top}']
    return cmd
