from pathlib import Path

from fault.user_cfg import FaultConfig
from .skill import run_skill

GET_BBOX = '''\
fp = outfile("{file_name}" "w")
cv = dbOpenCellViewByType("{lib}" "{cell}" "{view}" "maskLayout" "r")
bBox = cv~>prBoundary~>bBox
fprintf(fp, "%L %L %L %L", nth(0 nth(0 bBox)), nth(1 nth(0 bBox)), nth(0 nth(1 bBox)), nth(1 nth(1 bBox)))'''  # noqa


class BBox:
    def __init__(self, llx, lly, urx, ury):
        self.llx = llx
        self.lly = lly
        self.urx = urx
        self.ury = ury

    def __str__(self):
        return f'BBox({self.llx}, {self.lly}, {self.urx}, {self.ury})'

    def at_top(self, e, th=0.001):
        return 1 - th < (e.y - self.lly) / self.height < 1 + th

    def at_bottom(self, e, th=0.001):
        return -th < (e.y - self.lly) / self.height < +th

    def at_right(self, e, th=0.001):
        return 1 - th < (e.x - self.llx) / self.width < 1 + th

    def at_left(self, e, th=0.001):
        return -th < (e.x - self.llx) / self.width < +th

    @property
    def width(self):
        return self.urx - self.llx

    @property
    def height(self):
        return self.ury - self.lly


def get_bbox(lib, cell, view, cds_lib=None, cwd=None, script=None):
    # set defaults
    if cwd is None:
        cwd = FaultConfig.cwd
    if cds_lib is None:
        cds_lib = FaultConfig.cds_lib
    if script is None:
        script = f'bbox_{cell}'

    # run skill commands to get the bounding box
    lfile = Path(cwd).resolve() / 'bbox.txt'
    skill_cmds = GET_BBOX.format(
        file_name=lfile,
        lib=lib,
        cell=cell,
        view=view
    )
    run_skill(skill_cmds, cds_lib=cds_lib, script=script)

    # read bounding box results
    with open(lfile, 'r') as f:
        text = f.readlines()[0]
    vals = [float(tok) for tok in text.split()]

    # return bounding box object
    return BBox(
        llx=vals[0],
        lly=vals[1],
        urx=vals[2],
        ury=vals[3]
    )
