import os
from pathlib import Path

from fault.user_cfg import FaultConfig
from .skill import run_skill
from .transform import trmat

try:
    import numpy as np
except ModuleNotFoundError:
    print('Failed to import numpy for LayoutLabel.')


CREATE_LABEL = '''\
dbCreateLabel({cell_view} list("{layer}" "{purpose}") list({x} {y}) "{text}" "{justify}" "{orient}" "{font}" {height})'''  # noqa


GET_LABELS = '''\
fp = outfile("{file_name}" "w")
cv = dbOpenCellViewByType("{lib}" "{cell}" "{view}" "maskLayout" "r")
foreach(shape cv~>shapes
    if(shape~>objType == "label" then
        fprintf(fp, "%L, %L, %L, %L, %L, %L, %L\\n", shape~>lpp, shape~>xy, shape~>theLabel, shape~>justify, shape~>orient, shape~>font, shape~>height)
    )
)'''  # noqa


class LayoutLabel:
    def __init__(self, text, x=None, y=None, point=None, layer='M1',
                 purpose='label', justify='centerCenter', orient='R0',
                 font='stick', height=0.03):
        # two ways to specify the location:
        # 1) values for x and y
        # 2) numpy array with two values: [x, y]

        if x is not None and y is not None:
            assert point is None
            point = np.array([x, y], dtype=float)
        elif point is not None:
            assert x is None and y is None
            x = point[0]
            y = point[1]

        # save settings
        self.text = text
        self.x = x
        self.y = y
        self.point = point
        self.layer = layer
        self.purpose = purpose
        self.justify = justify
        self.orient = orient
        self.font = font
        self.height = height

    def __str__(self):
        return f'LayoutLabel("{self.text}")'

    def transform(self, kind):
        # TODO: update orientation of label
        point = trmat(kind).dot(self.point)
        return LayoutLabel(text=self.text, point=point, layer=self.layer,
                           purpose=self.purpose, justify=self.justify,
                           orient=self.orient, font=self.font,
                           height=self.height)

    def translate(self, xoff, yoff):
        off = np.array([xoff, yoff], dtype=float)
        point = self.point + off
        return LayoutLabel(text=self.text, point=point, layer=self.layer,
                           purpose=self.purpose, justify=self.justify,
                           orient=self.orient, font=self.font,
                           height=self.height)

    def rename(self, text):
        return LayoutLabel(text=text, point=self.point, layer=self.layer,
                           purpose=self.purpose, justify=self.justify,
                           orient=self.orient, font=self.font,
                           height=self.height)

    def create_cmd(self, cell_view):
        # return the label
        return CREATE_LABEL.format(
            cell_view=cell_view,
            layer=self.layer,
            purpose=self.purpose,
            x=self.x,
            y=self.y,
            text=self.text,
            justify=self.justify,
            orient=self.orient,
            font=self.font,
            height=self.height
        )

    @staticmethod
    def from_string(s):
        tokens = [tok.strip() for tok in s.split(',')]
        lpp = tokens[0][1:-1].split()
        xy = tokens[1][1:-1].split()
        layer = lpp[0].strip()[1:-1]
        purpose = lpp[1].strip()[1:-1]
        x = float(xy[0].strip())
        y = float(xy[1].strip())
        text = tokens[2][1:-1]
        justify = tokens[3][1:-1]
        orient = tokens[4][1:-1]
        font = tokens[5][1:-1]
        height = float(tokens[6])
        return LayoutLabel(layer=layer, purpose=purpose, x=x, y=y, text=text,
                           justify=justify, orient=orient, font=font,
                           height=height)


def get_labels(lib, cell, view, cds_lib=None, cwd=None,
               script=None):
    # determine working directory
    if cwd is None:
        cwd = FaultConfig.cwd
    cwd = Path(cwd).resolve()
    os.makedirs(cwd, exist_ok=True)

    # determine script name if needed
    if script is None:
        script = cwd / f'labels_{cell}.sh'

    # run skill code to get label locations
    lafile = cwd / f'labels_{cell}.txt'
    skill_cmds = GET_LABELS.format(
        file_name=lafile,
        lib=lib,
        cell=cell,
        view=view
    )
    run_skill(skill_cmds, cds_lib=cds_lib, cwd=cwd, script=script)

    # parse results
    labels = []
    with open(lafile, 'r') as f:
        for line in f:
            labels += [LayoutLabel.from_string(line)]

    # return list of labels
    return labels
