from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from fault import FaultConfig, si_netlist
from fault.spice import SpiceNetlist
from copy import deepcopy
from .create import instantiate_into
try:
    from decida.SimulatorNetlist import SimulatorNetlist
except ModuleNotFoundError:
    print('Failed to import DeCiDa.  SPICE capabilities will be limited.')


class Instance:
    def __init__(self, obj, name=None, x=0, y=0, orient='R0'):
        self.obj = obj
        self.x = x
        self.y = y
        self.orient = orient
        self.name = name

    @property
    def lib(self):
        return self.obj.lib

    @property
    def cell(self):
        return self.obj.cell

    @property
    def layout_view(self):
        return self.obj.layout_view


class GridDesign:
    def __init__(self, grid, cell, lib=None, layout_view='layout',
                 cds_lib=None, top=None, bottom=None, left=None,
                 right=None):
        # set defaults
        if top is None:
            top = []
        if bottom is None:
            bottom = []
        if left is None:
            left = []
        if right is None:
            right = []

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
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right

    def gen_labels(self, inst, kind):
        # build dictionary mapping instance label names to label objects
        # the order is that in which the pins should be mapped
        inst_labels = []
        for label in inst.obj.labels:
            if getattr(inst.obj.bbox, f'at_{kind}')(label):
                inst_labels.append(label)
        if kind in {'top', 'bottom'}:
            inst_labels = sorted(inst_labels, key=lambda e: +e.x)
        else:
            inst_labels = sorted(inst_labels, key=lambda e: -e.y)

        # return list of generated labels
        labels = []
        for inst_label in inst_labels:
            if self.lcount[kind] >= len(getattr(self, kind)):
                return labels
            else:
                # make a copy of the label and change some properties
                label = deepcopy(inst_label)
                label.text = getattr(self, kind)[self.lcount[kind]]
                label.x += inst.x
                label.y += inst.y
                # add label to list of labels to create
                labels.append(label)
                # increment the label count
                self.lcount[kind] += 1
        return labels

    def write_layout(self):
        # write instances
        instances = []
        labels = []
        inst_count = 0
        y = 0
        self.lcount = {
            'top': 0,
            'bottom': 0,
            'left': 0,
            'right': 0
        }
        for idx_i, row in enumerate(self.grid):
            x = 0
            for idx_j, elem in enumerate(row):
                # handle placement
                iname = f'I{inst_count}'
                inst_count += 1
                ix = x - elem.llx
                iy = y - elem.lly
                inst = Instance(elem, x=ix, y=iy, name=iname)
                instances.append(inst)
                # handle labeling
                if idx_i == 0:
                    labels += self.gen_labels(inst, 'top')
                if idx_i == len(self.grid):
                    labels += self.gen_labels(inst, 'bottom')
                if idx_j == 0:
                    labels += self.gen_labels(inst, 'left')
                if idx_j == len(row):
                    labels += self.gen_labels(inst, 'right')
                x += elem.width
            y -= row[0].height
        instantiate_into(self, instances, labels)
