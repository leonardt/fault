import os
from pathlib import Path
from itertools import count
from fault import FaultConfig, si_netlist
from fault.spice import SpiceNetlist
from fault.user_cfg import FaultConfig
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
                 right=None, print_status=True):

        if print_status:
            FaultConfig.print(f'Creating GridDesign {cell}.', level=1)

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

        # determine library automatically if it has
        # not been determined already
        if lib is None:
            lib = self.grid[0][0].mod.lib

        # name instances
        self.name_instances()

        # place instances
        self.place_instances()

        # generate bbox
        bbox = self.gen_bbox()

        # generate top, bottom, left, right as label arrays
        top_labels = self.gen_labels('top', self.get_row(0), top)
        bottom_labels = self.gen_labels('bottom', self.get_row(-1), bottom)
        left_labels = self.gen_labels('left', self.get_col(0), left)
        right_labels = self.gen_labels('right', self.get_col(-1), right)

        # write layout
        all_labels = top_labels + bottom_labels + left_labels + right_labels
        self.gen_layout(lib=lib, cell=cell, view=layout_view,
                        bbox=bbox, labels=all_labels)

        # generate connectivity between cells
        self.connect_cells()

        # attach pin names to edges
        self.attach_pin_names('top', self.get_row(0), top)
        self.attach_pin_names('bottom', self.get_row(-1), bottom)
        self.attach_pin_names('left', self.get_col(0), left)
        self.attach_pin_names('right', self.get_col(-1), right)

        # give names to unnamed internal signals
        self.name_internal_nets()

        # determine if any cells are non-empty (detail needed for LVS)
        # "empty" generally means that the cell entirely consists of
        # wiring, which means that its subckt definition would be empty
        # (i.e., connections would be made at a higher level)
        empty = all(all(elem.mod.empty for elem in row) for row in self.grid)

        # write netlist
        all_label_names = top + bottom + left + right
        spice_netlist = self.gen_netlist(cell=cell, labels=all_label_names)

        # call the super constructor
        super().__init__(lib=lib, cell=cell, layout_view=layout_view,
                         schematic_view=None, cds_lib=cds_lib, bbox=bbox,
                         top=top_labels, bottom=bottom_labels,
                         left=left_labels, right=right_labels,
                         empty=empty, spice_netlist=spice_netlist,
                         print_status=False)

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

    def gen_labels(self, kind, insts, names):
        # get flattened list of instances along this edge
        inst_labels = [inst_label
                       for inst in insts
                       for inst_label in getattr(inst, kind)]
        # return list of labels that have the correct external pin
        # name added
        retval = []
        for inst_label, pin_name in zip(inst_labels, names):
            if pin_name is not None:
                retval.append(inst_label.rename(pin_name))
        return retval

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

    def connect_cells(self):
        # loop over the instances
        for ii, row in enumerate(self.grid):
            for jj, elem in enumerate(row):
                # wire to module at left
                if jj > 0:
                    nets_to_left = self.grid[ii][jj - 1].edge_nets('right')
                    elem.wire_edge('left', nets_to_left)
                else:
                    elem.create_edge('left')
                # wire to module above
                if ii > 0:
                    nets_above = self.grid[ii - 1][jj].edge_nets('bottom')
                    elem.wire_edge('top', nets_above)
                else:
                    elem.create_edge('top')
                # create nets on right and bottom
                elem.create_edge('right')
                elem.create_edge('bottom')

    def attach_pin_names(self, kind, insts, names):
        # get flattened list of nets along this edge
        edge_nets = [edge_net
                     for inst in insts
                     for edge_net in inst.edge_nets(kind)]
        # name all of the nets in the correct order
        for (edge_net, pin_name) in zip(edge_nets, names):
            if pin_name is not None:
                edge_net.name = pin_name

    def name_internal_nets(self):
        tmpno = count()
        for row in self.grid:
            for elem in row:
                for net in elem.net_conn.values():
                    if net.name is None:
                        net.name = f'n{next(tmpno)}'

    def gen_netlist(self, cell, labels):
        # memoization for netlist generation of subcircuits
        memo_d = {}

        def memo_name(elem):
            return f'{elem.mod.cell}'

        def netlist_elem(elem):
            if memo_name(elem) in memo_d:
                return

            # determine file name for netlisted cell
            if elem.mod.spice_netlist is not None:
                fname = elem.mod.spice_netlist
            else:
                fname = si_netlist(lib=elem.mod.lib, cell=elem.mod.cell)

            # determine port order for netlisted cell
            parse = SimulatorNetlist(f'{fname}')
            ports = parse.get_subckt(elem.mod.cell.lower(), detail='ports')

            # store result
            memo_d[memo_name(elem)] = (fname, ports)

        def get_fname(elem):
            return memo_d[memo_name(elem)][0]

        def get_ports(elem):
            return memo_d[memo_name(elem)][1]

        # netlist cells as necessary
        for row in self.grid:
            for elem in row:
                if not elem.mod.empty:
                    netlist_elem(elem)

        # then start generating netlist for the cell itself
        netlist = SpiceNetlist()
        netlist.comment(f'Auto-generated netlist for {cell}')
        for val in memo_d.values():
            netlist.include(val[0])

        # determine port information
        ports = set(labels)
        if None in ports:
            ports.remove(None)
        ports = sorted(ports)

        # declare the circuit
        netlist.start_subckt(cell, *ports)

        # instantiate the cells
        for row in self.grid:
            for elem in row:
                if elem.mod.empty:
                    continue
                # "mapping" is a dictionary mapping a port on the subckt
                # to a net name.  both are just strings
                mapping = {key: val.name for key, val in elem.net_conn.items()}
                # "order" is just a list of ports of the subckt to be
                # instantiated in order
                order = get_ports(elem)
                iports = netlist.ordered_ports(mapping=mapping, order=order)
                netlist.instantiate(elem.mod.cell, *iports,
                                    inst_name=elem.inst_name)

        # end the subcircuit definition
        netlist.end_subckt()

        # write netlist to file and return path to the netlist
        cwd = Path(FaultConfig.cwd).resolve()
        os.makedirs(cwd, exist_ok=True)
        netlist_f = cwd / f'{cell}.sp'
        netlist.write_to_file(netlist_f)

        # return the netlist location
        return netlist_f
