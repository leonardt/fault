import os
from pathlib import Path

from fault.user_cfg import FaultConfig
from .skill import run_skill
from .transform import trmat

try:
    import numpy as np
except ModuleNotFoundError:
    print('Failed to import numpy for BBox.')


GET_BBOX = '''\
fp = outfile("{file_name}" "w")
cv = dbOpenCellViewByType("{lib}" "{cell}" "{view}" "maskLayout" "r")
bBox = cv~>prBoundary~>bBox
fprintf(fp, "%L %L %L %L", nth(0 nth(0 bBox)), nth(1 nth(0 bBox)), nth(0 nth(1 bBox)), nth(1 nth(1 bBox)))'''  # noqa


class BBox:
    def __init__(self, llx=None, lly=None, urx=None, ury=None, corners=None):
        # two ways to instantiate:
        # 1) by providing llx/lly/urx/ury (corners must be None)
        # 2) by providing a 2x4 array of corners (llx/lly/urx/ury must be None)

        if corners is None:
            assert all(v is not None for v in [llx, lly, urx, ury])
            corners = np.array([[llx, urx, urx, llx],
                                [lly, lly, ury, ury]], dtype=float)
        else:
            assert all(v is None for v in [llx, lly, urx, ury])
            llx = float(np.min(corners[0, :]))
            lly = float(np.min(corners[1, :]))
            urx = float(np.max(corners[0, :]))
            ury = float(np.max(corners[1, :]))

        # save settings
        self.llx = llx
        self.lly = lly
        self.urx = urx
        self.ury = ury
        self.corners = corners

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

    def transform(self, kind):
        return BBox(corners=trmat(kind).dot(self.corners))

    def translate(self, xoff, yoff):
        corners = self.corners
        corners[0, :] += xoff
        corners[1, :] += yoff
        return BBox(corners=corners)

    @property
    def width(self):
        return self.urx - self.llx

    @property
    def height(self):
        return self.ury - self.lly


def get_bbox(lib, cell, view, cds_lib=None, cwd=None, script=None):
    # get working directory
    if cwd is None:
        cwd = FaultConfig.cwd
    cwd = Path(cwd).resolve()
    os.makedirs(cwd, exist_ok=True)

    # determine script name if needed 
    if script is None:
        script = cwd / f'bbox_{cell}.sh'

    # run skill commands to get the bounding box
    bbfile = cwd / f'bbox_{cell}.txt'
    skill_cmds = GET_BBOX.format(
        file_name=bbfile,
        lib=lib,
        cell=cell,
        view=view
    )
    run_skill(skill_cmds, cds_lib=cds_lib, script=script)

    # read bounding box results
    with open(bbfile, 'r') as f:
        text = f.readlines()[0]
    vals = [float(tok) for tok in text.split()]

    # return bounding box object
    return BBox(
        llx=vals[0],
        lly=vals[1],
        urx=vals[2],
        ury=vals[3]
    )
