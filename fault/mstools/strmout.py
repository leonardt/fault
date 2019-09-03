import os
from fault.subprocess_run import subprocess_run


def strmout(lib, cell, cwd='.', run_dir='.', view='layout', out=None,
            env=None, add_to_env=None, log='strmOut.log', no_warn=None):
    # NOTE: cwd should be set to the directory that contains the cds.lib
    # file.

    # set defaults
    if out is None:
        out = f'{cell}.gds'
    if no_warn is None:
        # TODO: What do these numbers correspond to?  They're set
        # automatically by the CAD tool GUI.
        no_warn = [156, 246, 269, 270]

    # create the output directory if needed
    os.makedirs(cwd, exist_ok=True)
    os.makedirs(run_dir, exist_ok=True)

    # construct the command
    args = []
    args += ['strmout']
    args += ['-library', lib]
    args += ['-strmFile', out]
    args += ['-topCell', cell]
    args += ['-view', view]
    args += ['-logFile', log]
    args += ['-runDir', run_dir]
    if len(no_warn) > 0:
        args += ['-noWarn', ' '.join(f'{w}' for w in no_warn)]

    # run the command
    subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env)
