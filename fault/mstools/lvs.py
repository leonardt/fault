import os
from pathlib import Path
from fault.subprocess_run import subprocess_run


rul_tmpl = '''\
// layout location
LAYOUT SYSTEM '{layout_system}'
LAYOUT PRIMARY '{layout_primary}'
LAYOUT PATH '{layout_path}'

// schematic location
SOURCE SYSTEM '{source_system}'
SOURCE PRIMARY '{source_primary}'
SOURCE PATH '{source_path}'

// location of LVS report
LVS REPORT '{lvs_report}'

// location of output results
MASK SVDB DIRECTORY '{svdb_directory}' QUERY XRC

// formatting information for the extracted netlist
PEX NETLIST {xrc_netlist} {netlist_format} 1 SOURCENAMES

// TODO: Why is this option needed?  The MASK SVDB
// option seems to fail without it (and is required
// in order for PEX for work)
DRC ICSTATION YES

{include_files}
'''


def lvs(*args, **kwargs):
    xrc(*args, lvs_only=True, **kwargs)


def xrc(layout, schematic, rules=None, cwd='.', env=None, add_to_env=None,
        lvs_report='lvs.report', layout_system='GDSII', source_system='SPICE',
        source_primary=None, layout_primary=None, nl='\n',
        svdb_directory='svdb', xrc_netlist=None, netlist_format='HSPICE',
        lvs_only=False, lvs_netlist=None):

    # set defaults
    if rules is None:
        rules = []
    if source_primary is None:
        source_primary = Path(schematic).stem
    if layout_primary is None:
        layout_primary = Path(layout).stem
    if xrc_netlist is None:
        xrc_netlist = f'{source_primary}.sp'
    if lvs_netlist is None:
        lvs_netlist = Path(svdb_directory) / f'{source_primary}.sp'

    # path wrapping
    cwd = Path(cwd)

    # create the output directory if needed
    os.makedirs(cwd, exist_ok=True)

    # format commands to source in external files
    include_files = [f"INCLUDE '{rule}'" for rule in rules]
    include_files = nl.join(include_files)

    # write command file
    rul = rul_tmpl.format(
        layout_system=layout_system,
        layout_primary=layout_primary,
        layout_path=f'{layout}',
        source_system=source_system,
        source_primary=source_primary,
        source_path=f'{schematic}',
        lvs_report=f'{lvs_report}',
        svdb_directory=svdb_directory,
        xrc_netlist=f'{xrc_netlist}',
        netlist_format=netlist_format,
        include_files=include_files
    )
    rul_file = cwd / 'cal_xrc.rul'
    with open(rul_file, 'w') as f:
        f.write(rul)

    # Step 1: LVS
    # if lvs_only is True, then return afterwards (otherwise continue with
    # extraction)
    def xrc_lvs():
        args = []
        args += ['calibre']
        args += ['-lvs']
        args += ['-hier']
        args += ['-spice', f'{lvs_netlist}']
        args += [f'{rul_file}']
        subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env,
                       err_str='INCORRECT')
    xrc_lvs()
    if lvs_only:
        return

    # Step 2: PDB
    def xrc_pdb():
        args = []
        args += ['calibre']
        args += ['-xrc', '-pdb']
        args += ['-turbo']
        args += [f'-{type}']
        args += [f'{rul_file}']
        subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env)
    xrc_pdb()

    # Step 3: FMT
    def xrc_fmt():
        args = []
        args += ['calibre']
        args += ['-xrc', '-fmt']
        args += [f'-{type}']
        args += [f'{rul_file}']
        subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env)
    xrc_fmt()
