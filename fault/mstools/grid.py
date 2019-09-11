from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from fault import FaultConfig, si_netlist
from fault.subprocess_run import subprocess_run
from fault.spice import SpiceNetlist
from copy import deepcopy
try:
    from decida.SimulatorNetlist import SimulatorNetlist
except ModuleNotFoundError:
    print('Failed to import DeCiDa.  SPICE capabilities will be limited.')


OPEN_CELL_VIEW = '''\
{var} = dbOpenCellViewByType("{lib}" "{cell}" "{view}" "maskLayout" "{mode}")
'''


CREATE_INST = '''\
dbCreateInst({parent} {child} "{iname}" list({ix} {iy}) "R0")'''


def run_skill(skill_cmds, cds_lib):
    cwd = Path(cds_lib).resolve().parent
    with NamedTemporaryFile(dir='.', suffix='.il', mode='w') as f:
        f.write(skill_cmds)
        f.flush()
        args = []
        args += ['dbAccess']
        args += ['-load', str(Path(f.name).resolve())]
        subprocess_run(args, cwd=cwd, err_str='*Error*')


def var_name(x):
    return f'{x.lib}_{x.cell}_{x.layout_view}'


def open_cell_view(x, mode):
    return OPEN_CELL_VIEW.format(
        var=var_name(x),
        lib=x.lib,
        cell=x.cell,
        view=x.layout_view,
        mode=mode
    )


class GridDesign:
    def __init__(self, grid, cell, lib=None, layout_view='layout',
                 cds_lib=None):
        # wrap as necessary to get to a 2D grid
        if not isinstance(grid, list):
            grid = [grid]
        if not isinstance(grid[0], list):
            grid = [grid]

        # determine defaults
        if lib is None:
            lib = grid[0][0].lib
        if cds_lib is None:
            cds_lib = grid[0][0].cds_lib

        # save settings
        self.grid = grid
        self.cell = cell
        self.lib = lib
        self.layout_view = layout_view
        self.cds_lib = cds_lib

    def write_layout(self):
        # open cell views needed
        skill_cmds = []
        skill_cmds.append(open_cell_view(self, 'w'))
        read_cells = {}
        for row in self.grid:
            for elem in row:
                read_cells[var_name(elem)] = elem
        for val in read_cells.values():
            skill_cmds.append(open_cell_view(val, 'r'))

        # stamp instances
        # then stamp out instances
        idx = 0
        y = 0
        for row in self.grid:
            x = 0
            for elem in row:
                iname = f'I{idx}'
                ix = x - elem.llx
                iy = y - elem.lly
                cmd = CREATE_INST.format(
                    parent=var_name(self),
                    child=var_name(elem),
                    iname=iname,
                    ix=ix,
                    iy=iy
                )
                skill_cmds.append(cmd)
                idx += 1
                x += elem.width
            y += row[0].height

        # save cell view
        skill_cmds.append(f'dbSave({var_name(self)})')

        # run the command
        run_skill('\n'.join(skill_cmds), cds_lib=self.cds_lib)
