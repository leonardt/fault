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


SKILL_CMDS = '''\
parent = dbOpenCellViewByType("{plib}" "{pcell}" "{pview}" "maskLayout" "w")
child = dbOpenCellViewByType("{clib}" "{ccell}" "{cview}" "maskLayout" "r")
{create_inst}
{create_label}
dbSave(parent)'''


GET_LABELS = '''\
fp = outfile("{file_name}" "w")
cv = dbOpenCellViewByType("{lib}" "{cell}" "{view}" "maskLayout" "r")
foreach(shape cv~>shapes
    if(shape~>objType == "label" then
        fprintf(fp, "%L, %L, %L, %L, %L, %L, %L\\n", shape~>lpp, shape~>xy, shape~>theLabel, shape~>justify, shape~>orient, shape~>font, shape~>height)
    )
)'''  # noqa


CREATE_INST = '''\
dbCreateInst(parent child "{iname}" list({ix} {iy}) "R0")'''


CREATE_LABEL = '''\
dbCreateLabel({cell_view} list("{layer}" "{purpose}") list({x} {y}) "{text}" "{justify}" "{orient}" "{font}" {height})'''  # noqa


def nobus(name):
    if '<' in name:
        return name[:name.index('<')]
    else:
        return name


def busbit(name, bit, bussize):
    if name is None:
        return None
    elif bussize == 1:
        return f'{name}'
    else:
        return f'{name}<{bit}>'


def run_skill(skill_cmds, cds_lib):
    cwd = Path(cds_lib).resolve().parent
    with NamedTemporaryFile(dir='.', suffix='.il', mode='w') as f:
        f.write(skill_cmds)
        f.flush()
        args = []
        args += ['dbAccess']
        args += ['-load', str(Path(f.name).resolve())]
        subprocess_run(args, cwd=cwd, err_str='*Error*')


class LayoutLabel:
    def __init__(self, layer, purpose, x, y, text, justify, orient,
                 font, height):
        self.layer = layer
        self.purpose = purpose
        self.x = x
        self.y = y
        self.text = text
        self.justify = justify
        self.orient = orient
        self.font = font
        self.height = height

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


class RectCell:
    def __init__(self, lib, cell, width=0, height=0, child=None, nx=1,
                 ny=1, layout_view='layout', schematic_view='schematic',
                 cds_lib=None, left=None, right=None, top=None, bottom=None):
        # set defaults
        if cds_lib is None:
            cds_lib = FaultConfig.cds_lib
        if left is None:
            left = []
        if right is None:
            right = []
        if top is None:
            top = []
        if bottom is None:
            bottom = []

        # save settings
        self.lib = lib
        self.cell = cell
        self.layout_view = layout_view
        self.schematic_view = schematic_view
        self.width = width
        self.height = height
        self.child = child
        self.nx = nx
        self.ny = ny
        self.cds_lib = cds_lib
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom

    def array(self, nx=1, ny=1, cell=None, lib=None, layout_view=None,
              schematic_view=None):
        # set defaults
        if lib is None:
            lib = self.lib
        if cell is None:
            cell = self.cell
        if layout_view is None:
            layout_view = self.layout_view
        if schematic_view is None:
            schematic_view = self.schematic_view

        # generate top/bottom connections
        top = []
        bottom = []
        for k in range(nx):
            for tname in self.top:
                top.append(busbit(tname, k, nx))
            for bname in self.bottom:
                bottom.append(busbit(bname, k, nx))

        # generate left/right connections
        left = []
        right = []
        for k in range(ny):
            for lname in self.left:
                left.append(busbit(lname, k, ny))
            for rname in self.right:
                right.append(busbit(rname, k, ny))

        # compute derived parameters
        width = nx * self.width
        height = ny * self.height
        return RectCell(lib=lib, cell=cell, width=width, height=height,
                        child=self, nx=nx, ny=ny, layout_view=layout_view,
                        schematic_view=schematic_view, left=left,
                        right=right, top=top, bottom=bottom)

    def write_layout(self):
        # first generate dependencies
        if self.child is None:
            return
        else:
            self.child.write_layout()

        # find out label locations
        labels = {}
        with TemporaryDirectory(dir='.') as d:
            lfile = Path(d).resolve() / 'labels.txt'
            skill_cmds = GET_LABELS.format(
                file_name=lfile,
                lib=self.child.lib,
                cell=self.child.cell,
                view=self.child.layout_view
            )
            run_skill(skill_cmds, cds_lib=self.child.cds_lib)
            with open(lfile, 'r') as f:
                for line in f:
                    label = LayoutLabel.from_string(line)
                    labels[label.text] = label

        # then stamp out instances
        idx = 0
        create_inst = []
        for x in range(self.nx):
            for y in range(self.ny):
                iname = f'I{idx}'
                ix = x * self.child.width
                iy = y * self.child.height
                line = CREATE_INST.format(iname=iname, ix=ix, iy=iy)
                create_inst.append(line)
                idx += 1
        create_inst = '\n'.join(create_inst)

        # write labels
        nets = []

        # generate top/bottom connections
        for k in range(self.nx):
            for tname, bname in zip(self.top, self.bottom):
                if tname == bname:
                    bname = None
                if tname is not None:
                    net = deepcopy(labels[nobus(tname)])
                    net.x += k * self.child.width
                    net.text = busbit(net.text, k, self.nx)
                    nets.append(net)
                if bname is not None:
                    net = deepcopy(labels[nobus(bname)])
                    net.x += k * self.child.width
                    net.y += (self.ny - 1) * self.child.height
                    net.text = busbit(net.text, k, self.nx)
                    nets.append(net)

        # generate left/right connections
        for k in range(self.ny):
            for lname, rname in zip(self.left, self.right):
                if lname == rname:
                    rname = None
                if lname is not None:
                    net = deepcopy(labels[nobus(lname)])
                    net.y += k * self.child.height
                    net.text = busbit(net.text, k, self.ny)
                    nets.append(net)
                if rname is not None:
                    net = deepcopy(labels[nobus(rname)])
                    net.x += (self.nx - 1) * self.child.width
                    net.y += k * self.child.height
                    net.text = busbit(net.text, k, self.ny)
                    nets.append(net)

        create_label = []
        for net in nets:
            create_label.append(net.create_cmd('parent'))
        create_label = '\n'.join(create_label)

        # generate skill commands
        skill_cmds = SKILL_CMDS.format(
            plib=self.lib,
            pcell=self.cell,
            pview=self.layout_view,
            clib=self.child.lib,
            ccell=self.child.cell,
            cview=self.child.layout_view,
            create_inst=create_inst,
            create_label=create_label
        )

        # run the command
        run_skill(skill_cmds, cds_lib=self.cds_lib)

    def write_netlist(self, cwd):
        # generate netlist from schematic if this is a leaf cell
        if self.child is None:
            return si_netlist(lib=self.lib, cell=self.cell,
                              cds_lib=self.cds_lib, cwd=cwd,
                              view=self.schematic_view)

        # otherwise generate netlist for child and find out its port order
        child_netlist = self.child.write_netlist(cwd)
        parser = SimulatorNetlist(f'{child_netlist}')
        child_search_name = f'{self.child.cell}'.lower()
        child_order = parser.get_subckt(child_search_name, detail='ports')

        # then start generating netlist for the cell itself
        netlist = SpiceNetlist()
        netlist.comment(f'Auto-generated netlist for {self.cell}')

        # include the child cell
        netlist.include(child_netlist)

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

        # declare temporary name
        def tmpnet(prefix, k, x, y):
            return f'tmp_{prefix}_{k}_{x}_{y}'

        # instantiate all circuits
        for x in range(self.nx):
            for y in range(self.ny):
                # initialize the mapping
                mapping = {}
                # wire top/bottom connections
                for k, (tn, bn) in enumerate(zip(self.child.top,
                                                 self.child.bottom)):
                    # handle straight-through wiring
                    if tn == bn:
                        mapping[tn] = busbit(tn, x, self.nx)
                        continue
                    # wire top
                    if tn is not None:
                        if y == 0:
                            mapping[tn] = busbit(tn, x, self.nx)
                        else:
                            mapping[tn] = tmpnet('tb', k, x, y - 1)
                    # wire bottom
                    if bn is not None:
                        if y == self.ny - 1:
                            mapping[bn] = busbit(bn, x, self.nx)
                        else:
                            mapping[bn] = tmpnet('tb', k, x, y)
                # wire left/right connections
                for k, (ln, rn) in enumerate(zip(self.left, self.right)):
                    # handle straight-through wiring
                    if ln == rn:
                        mapping[ln] = busbit(ln, y, self.ny)
                        continue
                    # wire left
                    if ln is not None:
                        if x == 0:
                            mapping[ln] = busbit(ln, y, self.ny)
                        else:
                            mapping[ln] = tmpnet('lr', k, x - 1, y)
                    # wire right
                    if rn is not None:
                        if x == self.nx - 1:
                            mapping[rn] = busbit(rn, y, self.ny)
                        else:
                            mapping[rn] = tmpnet('lr', k, x, y)
                # create the instance
                iports = netlist.ordered_ports(mapping=mapping,
                                               order=child_order)
                netlist.instantiate(self.child.cell, *iports)

        # end the subcircuit definition
        netlist.end_subckt()

        # write netlist to file and return path to the netlist
        netlist_f = Path(cwd).resolve() / f'{self.cell}.sp'
        netlist.write_to_file(netlist_f)
        return netlist_f
