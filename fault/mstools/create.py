import os
from pathlib import Path
from .skill import run_skill
from fault.user_cfg import FaultConfig


OPEN_CELL_VIEW = '''\
{var} = dbOpenCellViewByType("{lib}" "{cell}" "{view}" "maskLayout" "{mode}")
'''


CREATE_INST = '''\
dbCreateInst({parent} {child} "{name}" list({x} {y}) "{orient}")'''


CREATE_BOUNDARY = '''\
dbCreateRect({parent} list( "prBoundary" "boundary" ) list( {llx}:{lly} {urx}:{ury} ) )'''


def open_cell_view(x, mode):
    return OPEN_CELL_VIEW.format(
        var=var_name(x),
        lib=x.lib,
        cell=x.cell,
        view=x.view,
        mode=mode
    )


def create_inst(parent, child):
    return CREATE_INST.format(
        parent=var_name(parent),
        child=var_name(child),
        name=child.inst_name,
        x=child.xoff,
        y=child.yoff,
        orient=child.orient
    )


def create_boundary(parent, bbox):
    return CREATE_BOUNDARY.format(
        parent=var_name(parent),
        llx=bbox.llx,
        lly=bbox.lly,
        urx=bbox.urx,
        ury=bbox.ury
    )


def var_name(x):
    return f'{x.lib}_{x.cell}_{x.view}'


def save_cell(x):
    return f'dbSave({var_name(x)})'


class LayoutModule:
    def __init__(self, lib, cell, view):
        self.lib = lib
        self.cell = cell
        self.view = view


class LayoutInstance:
    def __init__(self, lib, cell, view, inst_name=None, xoff=None,
                 yoff=None, orient=None):
        self.lib = lib
        self.cell = cell
        self.view = view
        self.inst_name = inst_name
        self.xoff = xoff
        self.yoff = yoff
        self.orient = orient


def instantiate_into(parent, instances=None, labels=None,
                     script=None, cwd=None, bbox=None):
    # determine working directory
    if cwd is None:
        cwd = FaultConfig.cwd
    cwd = Path(cwd).resolve()
    os.makedirs(cwd, exist_ok=True)

    # determine script name if needed
    if script is None:
        script = cwd / f'gen_{parent.cell}.sh'

    # set defaults
    if instances is None:
        instances = []
    if labels is None:
        labels = []

    # open DB
    cmds = []
    cmds += [open_cell_view(parent, 'w')]
    # instantiate cells, opening them as necessary
    names = set()
    for inst in instances:
        if var_name(inst) not in names:
            cmds += [open_cell_view(inst, 'r')]
            names.add(var_name(inst))
        cmds += [create_inst(parent, inst)]
    for label in labels:
        cmds += [label.create_cmd(var_name(parent))]
    if bbox is not None:
        cmds += [create_boundary(parent, bbox)]
    # save DB
    cmds += [save_cell(parent)]

    # run the skill code
    run_skill('\n'.join(cmds), script=script, cwd=cwd)
