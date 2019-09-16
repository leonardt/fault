import os
from pathlib import Path

from fault import FaultConfig
from fault.codegen import CodeGenerator
from fault.spice_target import DeclareFromSpice
from fault.subprocess_run import subprocess_run, subprocess_run_batch


class RulGen(CodeGenerator):
    def layout(self, path, system='GDSII', primary=None):
        # set defaults
        if primary is None:
            primary = Path(path).stem

        # emit commands
        self.cmdln('LAYOUT', 'SYSTEM', system)
        self.cmdln('LAYOUT', 'PRIMARY', self.quoted(primary))
        self.cmdln('LAYOUT', 'PATH', self.quoted(path))

    def source(self, path, system='SPICE', primary=None):
        # set defaults
        if primary is None:
            primary = Path(path).stem

        # emit commands
        self.cmdln('SOURCE', 'SYSTEM', system)
        self.cmdln('SOURCE', 'PRIMARY', self.quoted(primary))
        self.cmdln('SOURCE', 'PATH', self.quoted(path))

    def lvs_report(self, loc):
        self.cmdln('LVS', 'REPORT', self.quoted(loc))

    def mask_svdb(self, loc, query='XRC'):
        args = []
        args += ['MASK', 'SVDB']
        args += ['DIRECTORY', self.quoted(loc)]
        if query is not None:
            args += ['QUERY', query]
        self.cmdln(*args)

    def pex_netlist(self, loc, format='HSPICE', names='LAYOUTNAMES'):
        args = []
        args += ['PEX', 'NETLIST', self.quoted(loc)]
        if format is not None:
            # the "1" value means use a scale factor of "1"
            args += [format, '1']
        if names is not None:
            args += [names]
        self.cmdln(*args)

    def include(self, *files):
        for file in files:
            self.cmdln('INCLUDE', self.quoted(file))

    def cmdln(self, *args):
        self.println_space_sep(*args)

    def quoted(self, s):
        return f"'{s}'"


def lvs(layout, schematic, rules=None, cwd=None, env=None, add_to_env=None,
        lvs_report='lvs.report', layout_system='GDSII', source_system='SPICE',
        source_primary=None, layout_primary=None, rul_file='cal_lvs.rul',
        disp_type='on_error', script=None):
    # resolve paths
    layout = Path(layout).resolve()
    schematic = Path(schematic).resolve()

    # set defaults
    if cwd is None:
        cwd = FaultConfig.cwd
    if rules is None:
        rules = FaultConfig.cal_lvs_rules
    if source_primary is None:
        source_primary = schematic.stem
    if layout_primary is None:
        layout_primary = layout.stem
    if script is None:
        f'lvs_{layout_primary}.sh'

    # generate the command file
    gen = RulGen()
    gen.layout(system=layout_system, primary=layout_primary, path=layout)
    gen.source(system=source_system, primary=source_primary, path=schematic)
    gen.lvs_report(lvs_report)
    gen.include(*rules)

    # write the command file
    os.makedirs(cwd, exist_ok=True)
    gen.write_to_file(Path(cwd) / rul_file)

    # run the command
    args = []
    args += ['calibre']
    args += ['-lvs']
    args += ['-hier']
    args += [f'{rul_file}']
    subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env,
                   err_str='INCORRECT', disp_type=disp_type,
                   script=script)


def DeclareFromGDS(layout, *args, layout_primary=None, mode='digital',
                   **kwargs):
    # set defaults
    layout = Path(layout).resolve()
    if layout_primary is None:
        layout_primary = layout.stem

    # use extraction to create the SPICE netlist
    out = xrc(layout, *args, layout_primary=layout_primary, **kwargs)

    # create the circuit by parsing the SPICE netlist
    circuit = DeclareFromSpice(file_name=out, subckt_name=layout_primary,
                               mode=mode)

    # return the circuit
    return circuit


def xrc(layout, rules=None, cwd=None, env=None, add_to_env=None,
        lvs_report='lvs.report', layout_system='GDSII', layout_primary=None,
        svdb_directory='svdb', out=None, netlist_format='HSPICE',
        mode='c', rul_file='cal_xrc.rul', schematic=None,
        source_system='SPICE', source_primary=None, disp_type='on_error',
        script=None):
    # TODO: fix behavior when a schematic is specified

    # resolve paths
    layout = Path(layout).resolve()
    if schematic is not None:
        schematic = Path(schematic).resolve()

    # set location of working directory
    if cwd is None:
        cwd = FaultConfig.cwd
    cwd = Path(cwd).resolve()

    # set other defaults
    if cwd is None:
        cwd = FaultConfig.cwd
    if rules is None:
        rules = FaultConfig.cal_xrc_rules
    if layout_primary is None:
        layout_primary = layout.stem
    if source_primary is None and schematic is not None:
        source_primary = schematic.stem
    if out is None:
        out = cwd / f'{layout.stem}.sp'
    if script is None:
        script = f'xrc_{layout_primary}.sh'

    # make sure that output is a Path
    out = Path(out).resolve()

    # generate the command file
    gen = RulGen()
    gen.layout(system=layout_system, primary=layout_primary, path=layout)
    if schematic is not None:
        gen.source(system=source_system, primary=source_primary,
                   path=schematic)
    gen.lvs_report(lvs_report)
    gen.mask_svdb(svdb_directory, query='XRC')
    if schematic is not None:
        names = 'SOURCENAMES'
    else:
        names = 'LAYOUTNAMES'
    gen.pex_netlist(out, format=netlist_format, names=names)
    gen.cmdln('DRC', 'ICSTATION', 'YES')  # TODO: why is this command needed?
    gen.include(*rules)

    # write command file
    os.makedirs(cwd, exist_ok=True)
    gen.write_to_file(Path(cwd) / rul_file)

    # Step 1: LVS
    phdb = []
    phdb += ['calibre']
    phdb += ['-64']
    phdb += ['-xrc', '-phdb']
    phdb += [f'{rul_file}']

    # Step 2: PDB
    pdb = []
    pdb += ['calibre']
    pdb += ['-64']
    pdb += ['-xrc', '-pdb']
    pdb += [f'-{mode}']
    pdb += [f'{rul_file}']

    # Step 3: FMT
    fmt = []
    fmt += ['calibre']
    fmt += ['-64']
    fmt += ['-xrc', '-fmt']
    fmt += [f'-{mode}']
    fmt += [f'{rul_file}']

    # run the commands
    cmds = [phdb, pdb, fmt]
    subprocess_run_batch(cmds, cwd=cwd, env=env, add_to_env=add_to_env,
                         disp_type=disp_type, script=script)

    # return the location of the netlist (as a Path)
    return out
