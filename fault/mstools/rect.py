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


GET_BBOX = '''\
fp = outfile("{file_name}" "w")
cv = dbOpenCellViewByType("{lib}" "{cell}" "{view}" "maskLayout" "r")
bBox = cv~>bBox
fprintf(fp, "%L %L %L %L", nth(0 nth(0 bBox)), nth(1 nth(0 bBox)), nth(0 nth(1 bBox)), nth(1 nth(1 bBox)))
)'''  # noqa


def run_skill(skill_cmds, cds_lib):
    cwd = Path(cds_lib).resolve().parent
    with NamedTemporaryFile(dir='.', suffix='.il', mode='w') as f:
        f.write(skill_cmds)
        f.flush()
        args = []
        args += ['dbAccess']
        args += ['-load', str(Path(f.name).resolve())]
        subprocess_run(args, cwd=cwd, err_str='*Error*')


class RectCell:
    def __init__(self, lib, cell, layout_view='layout', cds_lib=None):
        # set defaults
        if cds_lib is None:
            cds_lib = FaultConfig.cds_lib

        # save settings
        self.lib = lib
        self.cell = cell
        self.layout_view = layout_view
        self.cds_lib = cds_lib

        # get the bounding box
        self.get_bbox()

    @property
    def width(self):
        return self.urx - self.llx

    @property
    def height(self):
        return self.ury - self.lly

    def get_bbox(self):
        with TemporaryDirectory(dir='.') as d:
            lfile = Path(d).resolve() / 'bbox.txt'
            skill_cmds = GET_BBOX.format(
                file_name=lfile,
                lib=self.lib,
                cell=self.cell,
                view=self.layout_view
            )
            run_skill(skill_cmds, cds_lib=self.cds_lib)
            with open(lfile, 'r') as f:
                text = f.readlines()[0]

        vals = [float(tok) for tok in text.split()]
        self.llx = vals[0]
        self.lly = vals[1]
        self.urx = vals[2]
        self.ury = vals[3]
