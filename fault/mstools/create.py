from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from .skill import run_skill


OPEN_CELL_VIEW = '''\
{var} = dbOpenCellViewByType("{lib}" "{cell}" "{view}" "maskLayout" "{mode}")
'''


CREATE_INST = '''\
dbCreateInst({parent} {child} "{name}" list({x} {y}) "{orient}")'''


def open_cell_view(x, mode):
    return OPEN_CELL_VIEW.format(
        var=var_name(x),
        lib=x.lib,
        cell=x.cell,
        view=x.layout_view,
        mode=mode
    )


def create_inst(parent, child):
    return CREATE_INST.format(
        parent=var_name(parent),
        child=var_name(child),
        name=child.name,
        x=child.x,
        y=child.y,
        orient=child.orient
    )


def save_cell(x):
    return f'dbSave({var_name(x)})'


def var_name(x):
    return f'{x.lib}_{x.cell}_{x.layout_view}'


def instantiate_into(parent, instances=None, labels=None):
    # open DB
    cmds = []
    cmds += [open_cell_view(parent, 'w')]
    # instantiate cells, opening them as necessary
    if instances is None:
        instances = []
    if labels is None:
        labels = []
    names = set()
    for inst in instances:
        if var_name(inst) not in names:
            cmds += [open_cell_view(inst, 'r')]
            names.add(var_name(inst))
        cmds += [create_inst(parent, inst)]
    for label in labels:
        cmds += [label.create_cmd(var_name(parent))]
    # save DB
    cmds += [save_cell(parent)]
    print(cmds)
    # run the skill code
    run_skill('\n'.join(cmds), cds_lib=parent.cds_lib)
