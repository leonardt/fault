from fault import FaultConfig
from .bbox import get_bbox
from .label import get_labels


class SpiceNet:
    def __init__(self, name=None):
        self.name = name


def sort_labels(labels, bbox):
    # find labels along top and sort left to right
    top = [e for e in labels if bbox.at_top(e)]
    top = sorted(top, key=lambda e: +e.x)
    
    # find labels along bottom and sort left to right
    bottom = [e for e in labels if bbox.at_bottom(e)]
    bottom = sorted(bottom, key=lambda e: +e.x)
    
    # find labels along the left edge and sort top to bottom
    left = [e for e in labels if bbox.at_left(e)]
    left = sorted(left, key=lambda e: -e.y)
    
    # find labels along the right edge and sort top to bottom
    right = [e for e in labels if bbox.at_right(e)]
    right = sorted(right, key=lambda e: -e.y)

    # return labels in order
    return top, bottom, left, right


class RectCellInst:
    def __init__(self, mod, xoff=0, yoff=0, orient='R0',
                 inst_name=None, net_conn=None):
        # set defaults
        if net_conn is None:
            net_conn = {}

        # save settings
        self.mod = mod
        self.xoff = xoff
        self.yoff = yoff
        self.orient = orient
        self.inst_name = inst_name
        self.net_conn = net_conn

        # update the geometry
        self.update_geometry()

    def update_geometry(self):
        # update bounding box
        bbox = self.mod.bbox
        bbox = bbox.transform(self.orient)
        bbox = bbox.translate(self.xoff, self.yoff)
        self.bbox = bbox

        # update the labels
        labels = [label for label in self.mod.labels]
        labels = [label.transform(self.orient) for label in labels]
        labels = [label.translate(self.xoff, self.yoff) for label in labels]
        top, bottom, left, right = sort_labels(labels=labels, bbox=bbox)
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right

    def transform(self, kind):
        self.orient = kind
        self.update_geometry()

    def translate(self, x, y):
        self.xoff += x
        self.yoff += y
        self.update_geometry()

    def edge_names(self, edge_kind):
        return [v.text for v in getattr(self, edge_kind)]

    def wire_edge(self, edge_kind, nets):
        # connect all pins along the given edge
        # to the list of SpiceNet objects provided
        edge_names = self.edge_names(edge_kind)
        for pin_name, net_obj in zip(edge_names, nets):
            self.net_conn[pin_name] = net_obj

    def create_edge(self, edge_kind):
        # create new SpiceNets for pins along this edge
        # if they haven't been created already
        edge_names = self.edge_names(edge_kind)
        for pin_name in edge_names:
            if pin_name not in self.net_conn:
                self.conn[pin_name] = SpiceNet()

    @property
    def labels(self):
        return self.top + self.bottom + self.left + self.right

    @property
    def llx(self):
        return self.bbox.llx

    @property
    def lly(self):
        return self.bbox.lly

    @property
    def urx(self):
        return self.bbox.urx

    @property
    def ury(self):
        return self.bbox.ury

    @property
    def width(self):
        return self.bbox.width

    @property
    def height(self):
        return self.bbox.height


class RectCellMod:
    def __init__(self, lib, cell, layout_view='layout',
                 schematic_view='schematic', cds_lib=None, bbox=None,
                 top=None, bottom=None, left=None, right=None,
                 empty=False, spice_netlist=None):

        # figure out bounding box if needed
        if bbox is None:
            bbox = get_bbox(lib=lib, cell=cell, view=layout_view,
                            cds_lib=cds_lib)

        # two ways to specify labels:
        # 1) automatically determined from the layout
        # 2) provide list for top/bottom/left/right
        if any(v is None for v in [top, bottom, left, right]):
            assert all(v is None for v in [top, bottom, left, right])

            # get list of all labels first
            labels = get_labels(lib=lib, cell=cell, view=layout_view,
                                cds_lib=cds_lib)

            # then sort into top/bottom/left/right
            top, bottom, left, right = sort_labels(labels=labels, bbox=bbox)
        else:
            assert all(v is not None for v in [top, bottom, left, right])

        # save settings
        self.lib = lib
        self.cell = cell
        self.layout_view = layout_view
        self.schematic_view = schematic_view
        self.bbox = bbox
        self.top = top
        self.bottom = bottom
        self.right = right
        self.left = left
        self.empty = empty
        self.spice_netlist = spice_netlist

    @property
    def labels(self):
        return self.top + self.bottom + self.left + self.right

    def make_inst(self):
        return RectCellInst(self)

    def transform(self, kind):
        return RectCellInst(self, kind)

