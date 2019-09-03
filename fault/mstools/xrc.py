import os
from pathlib import Path
from fault.subprocess_run import subprocess_run


cmd_tmpl = '''\
LAYOUT SYSTEM {layout_system}
LAYOUT PRIMARY '{layout_primary}'
LAYOUT PATH '{layout_path}'
LVS REPORT '{lvs_report}'

MASK SVDB DIRECTORY "svdb" QUERY XRC

PEX NETLIST {out} {netlist_format} 1 LAYOUTNAMES

DRC ICSTATION YES

{include_files}
'''


def xrc(layout, rules=None, cwd='.', env=None, add_to_env=None,
        lvs_report='lvs.report', out=None, dist_report='dist.report',
        c_cap_report='c_cap.report', netlist_format='HSPICE',
        layout_system='GDSII', layout_primary=None, nl='\n',
        type='c', extra_opts=None):

    # set defaults
    if rules is None:
        rules = []
    if layout_primary is None:
        layout_primary = Path(layout).stem
    if out is None:
        out = f'{layout_primary}.sp'
    if extra_opts is None:
        extra_opts = ['-64']

    # path wrapping
    cwd = Path(cwd)

    # create the output directory if needed
    os.makedirs(cwd, exist_ok=True)

    # format commands to source in external files
    include_files = [f'INCLUDE {rule}' for rule in rules]
    include_files = nl.join(include_files)

    # write command file
    cmd = cmd_tmpl.format(
        layout_system=layout_system,
        layout_primary=layout_primary,
        layout_path=f'{layout}',
        lvs_report=lvs_report,
        out=out,
        netlist_format=netlist_format,
        dist_report=dist_report,
        c_cap_report=c_cap_report,
        include_files=include_files
    )
    cmd_file = cwd / 'cal_xrc.rul'
    with open(cmd_file, 'w') as f:
        f.write(cmd)

    # Step 1: PHDB
    def xrc_phdb():
        args = []
        args += ['calibre']
        args += extra_opts
        args += ['-xrc', '-phdb']
        args += [f'{cmd_file}']
        subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env)
    xrc_phdb()

    # Step 2: PDB
    def xrc_pdb():
        args = []
        args += ['calibre']
        args += extra_opts
        args += ['-xrc', '-pdb']
        args += [f'-{type}']
        args += [f'{cmd_file}']
        subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env)
    xrc_pdb()

    # Step 3: FMT
    def xrc_fmt():
        args = []
        args += ['calibre']
        args += extra_opts
        args += ['-xrc', '-fmt']
        args += [f'-{type}']
        args += [f'{cmd_file}']
        subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env)
    xrc_fmt()
