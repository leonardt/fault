from fault import FaultConfig
from .label import get_labels
from .bbox import get_bbox
try:
    from decida.SimulatorNetlist import SimulatorNetlist
except ModuleNotFoundError:
    print('Failed to import DeCiDa.  SPICE capabilities will be limited.')


class RectCell:
    def __init__(self, lib, cell, layout_view='layout', cds_lib=None,
                 bbox=None, labels=None, top=None, bottom=None,
                 left=None, right=None, instantiate=True):
        # set defaults
        if cds_lib is None:
            cds_lib = FaultConfig.cds_lib
        if bbox is None:
            bbox = get_bbox(lib=lib, cell=cell, view=layout_view,
                            cds_lib=cds_lib)
        if labels is None:
            labels = get_labels(lib=lib, cell=cell, view=layout_view,
                                cds_lib=cds_lib)
        if top is None:
            top = [e for e in labels if bbox.at_top(e)]
            top = sorted(top, key=lambda e: +e.x)
            top = [e.text for e in top]
        if bottom is None:
            bottom = [e for e in labels if bbox.at_bottom(e)]
            bottom = sorted(bottom, key=lambda e: +e.x)
            bottom = [e.text for e in bottom]
        if left is None:
            left = [e for e in labels if bbox.at_left(e)]
            left = sorted(left, key=lambda e: -e.y)
            left = [e.text for e in left]
        if right is None:
            right = [e for e in labels if bbox.at_right(e)]
            right = sorted(right, key=lambda e: -e.y)
            right = [e.text for e in right]

        # save settings
        self.lib = lib
        self.cell = cell
        self.layout_view = layout_view
        self.cds_lib = cds_lib
        self.bbox = bbox
        self.labels = labels
        self.top = top
        self.bottom = bottom
        self.right = right
        self.left = left
        self.instantiate = instantiate

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
