from copy import deepcopy
from pathlib import Path
from itertools import count
from fault import FaultConfig, si_netlist
from fault.spice import SpiceNetlist
from .create import instantiate_into, LayoutInstance, LayoutModule
from .rect import RectCellMod, RectCellInst
from .bbox import BBox

try:
    from decida.SimulatorNetlist import SimulatorNetlist
except ModuleNotFoundError:
    print('Failed to import DeCiDa.  SPICE capabilities will be limited.')


class GridDesign(RectCellMod):
    def __init__(self, grid, cell, lib=None, layout_view='layout',
                 cds_lib=None, top=None, bottom=None, left=None,
                 right=None):
        # wrap "grid" as necessary to make it 2D,
        # and make unique instances of modules as
        # necessary
        if not isinstance(grid, list):
            grid = [grid]
        if not isinstance(grid[0], list):
            grid = [grid]
        inst_grid = []
        for row in grid:
            inst_row = []
            for elem in row:
                if not isinstance(elem, RectCellInst):
                    elem = elem.make_inst()
                inst_row.append(elem)
            inst_grid.append(inst_row)
        self.grid = inst_grid
        
        # set defaults for edge connection names
        if top is None:
            top = []
        if bottom is None:
            bottom = []
        if left is None:
            left = []
        if right is None:
            right = []
        e_dict = {
            'top': top,
            'bottom': bottom,
            'left': left,
            'right': right
        }

        # determine library automatically if it has
        # not been determined already
        if lib is None:
            lib = grid[0][0].lib

        # name instances
        self.name_instances()

        # place instances
        self.place_instances()

        # generate bbox
        bbox = self.gen_bbox()

        # generate top, bottom, left, right as label arrays
        l_dict = self.gen_labels(e_dict)

        # write layout
        labels = []
        labels += l_dict['top']
        labels += l_dict['bottom']
        labels += l_dict['left']
        labels += l_dict['right']
        self.gen_layout(lib=lib, cell=cell, view=layout_view,
                        bbox=bbox, labels=labels)

        # write netlist
        # spice_netlist = self.gen_netlist()
        spice_netlist = None

        # determine if any cells are non-empty (detail needed for LVS)
        empty = all(all(elem.mod.empty for elem in row) for row in self.grid)

        # call the super constructor
        super().__init__(lib=lib, cell=cell, layout_view=layout_view,
                         schematic_view=None, cds_lib=cds_lib, bbox=bbox,
                         top=l_dict['top'], bottom=l_dict['bottom'],
                         left=l_dict['left'], right=l_dict['right'],
                         empty=empty, spice_netlist=spice_netlist)

    def get_row(self, num):
        return self.grid[num]

    def get_col(self, num):
        return [row[num] for row in self.grid]

    def name_instances(self):
        tmpno = count()
        for row in self.grid:
            for elem in row:
                if elem.inst_name is None:
                    elem.inst_name = f'I{next(tmpno)}'

    def place_instances(self):
        y = 0
        for row in self.grid:
            x = 0
            for elem in row:
                elem.translate(x - elem.llx, y - elem.ury)
                x += elem.width
            # figure out maximum height of everything in the grid,
            # then decrement y by that amount
            max_h = max(elem.height for elem in row)
            y -= max_h

    def gen_bbox(self):
        llx = +float('inf')
        lly = +float('inf')
        urx = -float('inf')
        ury = -float('inf')
        for row in self.grid:
            for elem in row:
                llx = min(elem.llx, llx)
                lly = min(elem.lly, lly)
                urx = max(elem.urx, urx)
                ury = max(elem.ury, ury)
        return BBox(llx=llx, lly=lly, urx=urx, ury=ury)

    def gen_labels(self, e_dict):
        edges = {
            'top': self.get_row(0),
            'bottom': self.get_row(-1),
            'left': self.get_col(0),
            'right': self.get_col(-1)
        }

        def gen_label_helper(kind):
            retval = []
            idx = 0
            for inst in edges[kind]:
                for inst_label in getattr(inst, kind):
                    if idx >= len(e_dict[kind]):
                        return retval
                    if e_dict[kind][idx] is not None:
                        label = inst_label.rename(e_dict[kind][idx])
                        retval.append(label)
                    idx += 1
            return retval

        return {key: gen_label_helper(key) for key in edges.keys()}

    def gen_layout(self, lib, cell, view, bbox, labels):
        insts = []
        for row in self.grid:
            for elem in row:
                inst = LayoutInstance(lib=elem.mod.lib,
                                      cell=elem.mod.cell,
                                      view=elem.mod.layout_view,
                                      inst_name=elem.inst_name,
                                      xoff=elem.xoff,
                                      yoff=elem.yoff,
                                      orient=elem.orient)
                insts.append(inst)
        parent = LayoutModule(lib=lib, cell=cell, view=view)
        instantiate_into(parent=parent, instances=insts, labels=labels,
                         bbox=bbox)

#    def name_pins(self, inst, kind, name_count):
#        # return list of generated labels
#        for inst_port in getattr(inst.obj, kind):
#            if name_count[kind] >= len(getattr(self, kind)):
#                return
#            else:
#                # name the net and increment the counter
#                port_list = getattr(self, kind)
#                inst.conn[inst_port].name = port_list[name_count[kind]]
#                name_count[kind] += 1
#
#    def write_netlist(self, cwd=None):
#        # set defaults
#        if cwd is None:
#            cwd = FaultConfig.cwd
#
#        # create a grid of spice instances
#        sgrid = []
#        inst_count = 0
#        for row in self.grid:
#            sgrid.append([])
#            for elem in row:
#                name = f'I{inst_count}'
#                sgrid[-1].append(SpiceInstance(obj=elem, name=name))
#                inst_count += 1
#
#        # loop over the instances
#        for ii, row in enumerate(sgrid):
#            for jj, elem in enumerate(row):
#                # wire to module at left
#                if jj > 0:
#                    right = []
#                    for name in sgrid[ii][jj - 1].obj.right:
#                        right.append(sgrid[ii][jj - 1].conn[name])
#                    elem.wire('left', right)
#                else:
#                    elem.create('left')
#                # wire to module above
#                if ii > 0:
#                    bottom = []
#                    for name in sgrid[ii - 1][jj].obj.bottom:
#                        bottom.append(sgrid[ii - 1][jj].conn[name])
#                    elem.wire('top', bottom)
#                else:
#                    elem.create('top')
#                # create nets on right and bottom
#                elem.create('right')
#                elem.create('bottom')
#
#        # assign net names
#        name_count = dict(top=0, bottom=0, left=0, right=0)
#        for elem in sgrid[0]:
#            self.name_pins(elem, 'top', name_count)
#        for elem in sgrid[-1]:
#            self.name_pins(elem, 'bottom', name_count)
#        for row in sgrid:
#            self.name_pins(row[0], 'left', name_count)
#        for row in sgrid:
#            self.name_pins(row[-1], 'right', name_count)
#        tmpcount = 0
#        for ii, row in enumerate(sgrid):
#            for jj, elem in enumerate(row):
#                for net in elem.conn.values():
#                    if net.name is None:
#                        net.name = f'n{tmpcount}'
#                        tmpcount += 1
#
#        # generate a unique list of all instantiated cells,
#        # netlisting new cells as they are encountered
#        unique_cells = {}
#        for row in sgrid:
#            for elem in row:
#                if elem.obj.wiring:
#                    continue
#                elif elem.obj.cell not in unique_cells:
#                    fname = si_netlist(lib=elem.obj.lib,
#                                       cell=elem.obj.cell,
#                                       cds_lib=elem.obj.cds_lib,
#                                       cwd=cwd,
#                                       view='schematic')
#                    parser = SimulatorNetlist(f'{fname}')
#                    child_search_name = f'{elem.obj.cell}'.lower()
#                    child_order = parser.get_subckt(child_search_name,
#                                                    detail='ports')
#                    unique_cells[elem.obj.cell] = (fname, child_order)
#
#        # then start generating netlist for the cell itself
#        netlist = SpiceNetlist()
#        netlist.comment(f'Auto-generated netlist for {self.cell}')
#        for val in unique_cells.values():
#            netlist.include(val[0])
#
#        # determine port information
#        ports = set()
#        ports |= set(self.left)
#        ports |= set(self.right)
#        ports |= set(self.top)
#        ports |= set(self.bottom)
#        if None in ports:
#            ports.remove(None)
#        ports = sorted(ports)
#
#        # declare the circuit
#        netlist.start_subckt(self.cell, *ports)
#
#        # instantiate the cells
#        for row in sgrid:
#            for elem in row:
#                if elem.obj.wiring:
#                    continue
#                # create the instance
#                mapping = {key: val.name for key, val in elem.conn.items()}
#                child_order = unique_cells[elem.obj.cell][1]
#                iports = netlist.ordered_ports(mapping=mapping,
#                                               order=child_order)
#                netlist.instantiate(elem.obj.cell, *iports, inst_name=elem.name)
#
#        # end the subcircuit definition
#        netlist.end_subckt()
#
#        # write netlist to file and return path to the netlist
#        netlist_f = Path(cwd).resolve() / f'{self.cell}.sp'
#        netlist.write_to_file(netlist_f)
#        return netlist_f
