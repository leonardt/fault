from copy import deepcopy
from pathlib import Path

from fault import FaultConfig, si_netlist
from fault.spice import SpiceNetlist
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


class SpiceNet:
    def __init__(self, name=None):
        self.name = name


class SpiceInstance:
    def __init__(self, obj=None, name=None):
        self.obj = obj
        self.name = name
        self.conn = {}

    def wire(self, kind, other_nets):
        pin_names = getattr(self.obj, kind)
        for pin_name, other_net in zip(pin_names, other_nets):
            self.conn[pin_name] = other_net

    def create(self, kind):
        pin_names = getattr(self.obj, kind)
        for pin_name in pin_names:
            if pin_name not in self.conn:
                self.conn[pin_name] = SpiceNet()


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

    def name_pins(self, inst, kind):
        # return list of generated labels
        for inst_port in getattr(inst.obj, kind):
            if self.lcount[kind] >= len(getattr(self, kind)):
                return
            else:
                # name the net and increment the counter
                port_list = getattr(self, kind)
                inst.conn[inst_port].name = port_list[self.lcount[kind]]
                self.lcount[kind] += 1

    def write_netlist(self, cwd=None):
        # set defaults
        if cwd is None:
            cwd = FaultConfig.cwd

        # create a grid of spice instances
        sgrid = []
        inst_count = 0
        for row in self.grid:
            sgrid.append([])
            for elem in row:
                name = f'I{inst_count}'
                sgrid[-1].append(SpiceInstance(obj=elem, name=name))
                inst_count += 1

        # loop over the instances
        for ii, row in enumerate(sgrid):
            for jj, elem in enumerate(row):
                # wire to module at left
                if jj > 0:
                    right = []
                    for name in sgrid[ii][jj - 1].obj.right:
                        right.append(sgrid[ii][jj - 1].conn[name])
                    elem.wire('left', right)
                else:
                    elem.create('left')
                # wire to module above
                if ii > 0:
                    bottom = []
                    for name in sgrid[ii - 1][jj].obj.bottom:
                        bottom.append(sgrid[ii - 1][jj].conn[name])
                    elem.wire('top', bottom)
                else:
                    elem.create('top')
                # create nets on right and bottom
                elem.create('right')
                elem.create('bottom')

        # assign net names
        self.lcount = {
            'top': 0,
            'bottom': 0,
            'left': 0,
            'right': 0
        }
        for elem in sgrid[0]:
            self.name_pins(elem, 'top')
        for elem in sgrid[-1]:
            self.name_pins(elem, 'bottom')
        for row in sgrid:
            self.name_pins(row[0], 'left')
            self.name_pins(row[-1], 'right')
        tmpcount = 0
        for ii, row in enumerate(sgrid):
            for jj, elem in enumerate(row):
                for net in elem.conn.values():
                    if net.name is None:
                        net.name = f'n{tmpcount}'
                        tmpcount += 1

        # generate a unique list of all instantiated cells,
        # netlisting new cells as they are encountered
        unique_cells = {}
        for row in sgrid:
            for elem in row:
                if not elem.obj.instantiate:
                    continue
                elif elem.obj.cell not in unique_cells:
                    fname = si_netlist(lib=elem.obj.lib,
                                       cell=elem.obj.cell,
                                       cds_lib=elem.obj.cds_lib,
                                       cwd=cwd,
                                       view='schematic')
                    parser = SimulatorNetlist(f'{fname}')
                    child_search_name = f'{elem.obj.cell}'.lower()
                    child_order = parser.get_subckt(child_search_name,
                                                    detail='ports')
                    unique_cells[elem.obj.cell] = (fname, child_order)

        # then start generating netlist for the cell itself
        netlist = SpiceNetlist()
        netlist.comment(f'Auto-generated netlist for {self.cell}')
        for val in unique_cells.values():
            netlist.include(val[0])

        # determine port information
        ports = set()
        ports |= set(self.left)
        ports |= set(self.right)
        ports |= set(self.top)
        ports |= set(self.bottom)
        if None in ports:
            ports.remove(None)
        ports = sorted(ports)

        # declare the circuit
        netlist.start_subckt(self.cell, *ports)

        # instantiate the cells
        for row in sgrid:
            for elem in row:
                if not elem.obj.instantiate:
                    continue
                # create the instance
                mapping = {key: val.name for key, val in elem.conn.items()}
                child_order = unique_cells[elem.obj.cell][1]
                iports = netlist.ordered_ports(mapping=mapping,
                                               order=child_order)
                netlist.instantiate(elem.obj.cell, *iports, inst_name=elem.name)

        # end the subcircuit definition
        netlist.end_subckt()

        # write netlist to file and return path to the netlist
        netlist_f = Path(cwd).resolve() / f'{self.cell}.sp'
        netlist.write_to_file(netlist_f)
        return netlist_f
