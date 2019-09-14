import os
from pathlib import Path
from fault.subprocess_run import subprocess_run
from fault import FaultConfig


def strmout(lib, cell, cds_lib=None, cwd=None, view='layout', out=None,
            env=None, add_to_env=None, log='strmOut.log', no_warn=None,
            disp_mode='on_error'):
    # set defaults
    if cwd is None:
        cwd = FaultConfig.cwd

    # resolve paths
    cwd = Path(cwd).resolve()

    # set defaults
    if cds_lib is None:
        cds_lib = FaultConfig.cds_lib
    if out is None:
        out = cwd / f'{cell}.gds'
    if no_warn is None:
        # TODO: What do these numbers correspond to?  They're set
        # automatically by the CAD tool GUI.
        no_warn = [156, 246, 269, 270]

    # create the output directory if needed
    os.makedirs(cwd, exist_ok=True)

    # construct the command
    args = []
    args += ['strmout']
    args += ['-library', f'{lib}']
    args += ['-strmFile', f'{out}']
    args += ['-topCell', f'{cell}']
    args += ['-view', f'{view}']
    args += ['-logFile', f'{log}']
    args += ['-runDir', f'{cwd}']
    if len(no_warn) > 0:
        args += ['-noWarn', ' '.join(f'{w}' for w in no_warn)]

    # run the command
    launch_dir = Path(cds_lib).resolve().parent
    subprocess_run(args, cwd=launch_dir, env=env, add_to_env=add_to_env,
                   disp_mode=disp_mode)
