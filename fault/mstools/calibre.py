from pathlib import Path
from fault.subprocess_run import subprocess_run
from fault.codegen import CodeGenerator


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


def lvs(layout, schematic, rules=None, cwd='.', env=None, add_to_env=None,
        lvs_report='lvs.report', layout_system='GDSII', source_system='SPICE',
        source_primary=None, layout_primary=None):

    # set defaults
    if rules is None:
        rules = []
    if source_primary is None:
        source_primary = Path(schematic).stem
    if layout_primary is None:
        layout_primary = Path(layout).stem

    # generate the command file
    gen = RulGen()
    gen.layout(system=layout_system, primary=layout_primary, path=layout)
    gen.source(system=source_system, primary=source_primary, path=schematic)
    gen.lvs_report(lvs_report)
    gen.include(*rules)

    # write the command file
    rul_file = Path(cwd) / 'cal_lvs.rul'
    gen.write_to_file(rul_file)

    # run the command
    args = []
    args += ['calibre']
    args += ['-lvs']
    args += ['-hier']
    args += [f'{rul_file}']
    subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env,
                   err_str='INCORRECT')


def xrc(layout, rules=None, cwd='.', env=None, add_to_env=None,
        lvs_report='lvs.report', layout_system='GDSII', layout_primary=None,
        svdb_directory='svdb', xrc_netlist=None, netlist_format='HSPICE',
        mode='c'):

    # set defaults
    if rules is None:
        rules = []
    if layout_primary is None:
        layout_primary = Path(layout).stem
    if xrc_netlist is None:
        xrc_netlist = Path(layout).stem + '.sp'

    # generate the command file
    gen = RulGen()
    gen.layout(system=layout_system, primary=layout_primary, path=layout)
    gen.lvs_report(lvs_report)
    gen.mask_svdb(svdb_directory, query='XRC')
    gen.pex_netlist(xrc_netlist, format=netlist_format)
    gen.cmdln('DRC', 'ICSTATION', 'YES')  # TODO: why is this command needed?
    gen.include(*rules)

    # write command file
    rul_file = Path(cwd) / 'cal_xrc.rul'
    gen.write_to_file(rul_file)

    # Step 1: LVS
    def phdb():
        args = []
        args += ['calibre']
        args += ['-64']
        args += ['-xrc', '-phdb']
        args += [f'{rul_file}']
        subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env)
    phdb()

    # Step 2: PDB
    def pdb():
        args = []
        args += ['calibre']
        args += ['-64']
        args += ['-xrc', '-pdb']
        args += [f'-{mode}']
        args += [f'{rul_file}']
        subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env)
    pdb()

    # Step 3: FMT
    def fmt():
        args = []
        args += ['calibre']
        args += ['-64']
        args += ['-xrc', '-fmt']
        args += [f'-{mode}']
        args += [f'{rul_file}']
        subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env)
    fmt()
