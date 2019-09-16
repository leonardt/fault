import os
from pathlib import Path
from fault.subprocess_run import subprocess_run
from fault import FaultConfig
from .calibre import DeclareFromGDS


def DeclareFromLayout(lib, cell, *args, mode='digital', **kwargs):
    # stream out the layout to GDS
    out = strmout(lib, cell, *args, **kwargs)

    # declare the circuit from GDS
    circuit = DeclareFromGDS(layout=out, layout_primary=cell, mode=mode)

    # return the circuit
    return circuit


def strmout(lib, cell, cds_lib=None, cwd=None, view='layout', out=None,
            env=None, add_to_env=None, log='strmOut.log', no_warn=None,
            disp_type='on_error'):
    # set defaults
    if cwd is None:
        cwd = FaultConfig.cwd
    if cds_lib is None:
        cds_lib = FaultConfig.cds_lib
    if no_warn is None:
        # TODO: What do these numbers correspond to?  They're set
        # automatically by the CAD tool GUI.
        no_warn = [156, 246, 269, 270]

    # determine full path to working directory and create it if needed
    cwd = Path(cwd).resolve()
    os.makedirs(cwd, exist_ok=True)

    # set the output path
    if out is None:
        out = cwd / f'{cell}.gds'
    out = Path(out).resolve()

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
                   disp_type=disp_type)

    # return the output location
    return out
