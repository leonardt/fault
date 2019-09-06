from pathlib import Path
from tempfile import NamedTemporaryFile
from fault import FaultConfig
from fault.subprocess_run import subprocess_run


SKILL_CMDS = '''\
parent = dbOpenCellViewByType("{plib}" "{pcell}" "{pview}" "maskLayout" "w")
child = dbOpenCellViewByType("{clib}" "{ccell}" "{cview}" "maskLayout" "r")
{create_inst}
dbSave(parent)'''


CREATE_INST = '''\
dbCreateInst(parent child "{iname}" list({ix} {iy}) "R0")'''


class RectCell:
    def __init__(self, lib, cell, width=0, height=0, child=None, nx=1,
                 ny=1, view='layout', cds_lib=None):
        # set defaults
        if cds_lib is None:
            cds_lib = FaultConfig.cds_lib

        # save settings
        self.lib = lib
        self.cell = cell
        self.view = view
        self.width = width
        self.height = height
        self.child = child
        self.nx = nx
        self.ny = ny
        self.cds_lib = cds_lib

    def array(self, nx=1, ny=1, cell=None, lib=None, view=None):
        # set defaults
        if lib is None:
            lib = self.lib
        if cell is None:
            cell = self.cell
        if view is None:
            view = self.view

        # compute derived parameters
        width = nx * self.width
        height = ny * self.height
        return RectCell(lib=lib, cell=cell, width=width, height=height,
                        child=self, nx=nx, ny=ny)

    def write_layout(self):
        # first generate dependencies
        if self.child is None:
            return
        else:
            self.child.write_layout()

        # then write the layout
        idx = 0
        lines = []
        for x in range(self.nx):
            for y in range(self.ny):
                iname = f'I{idx}'
                ix = x * self.child.width
                iy = y * self.child.height
                line = CREATE_INST.format(iname=iname, ix=ix, iy=iy)
                lines.append(line)
                idx += 1
        lines = '\n'.join(lines)

        # generate skill commands
        skill_cmds = SKILL_CMDS.format(
            plib=self.lib,
            pcell=self.cell,
            pview=self.view,
            clib=self.child.lib,
            ccell=self.child.cell,
            cview=self.child.view,
            create_inst=lines
        )

        # run the command
        cwd = Path(self.cds_lib).resolve().parent
        with NamedTemporaryFile(dir='.', suffix='.il', mode='w') as f:
            f.write(skill_cmds)
            f.flush()
            args = []
            args += ['dbAccess']
            args += ['-load', str(Path(f.name).resolve())]
            subprocess_run(args, cwd=cwd)
