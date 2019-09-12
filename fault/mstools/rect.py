from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from fault import FaultConfig, si_netlist
from fault.subprocess_run import subprocess_run
from fault.spice import SpiceNetlist
from .label import get_labels
from .bbox import get_bbox
from copy import deepcopy
try:
    from decida.SimulatorNetlist import SimulatorNetlist
except ModuleNotFoundError:
    print('Failed to import DeCiDa.  SPICE capabilities will be limited.')


class RectCell:
    def __init__(self, lib, cell, layout_view='layout', cds_lib=None,
                 bbox=None, labels=None, top=None, bottom=None,
                 left=None, right=None):
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
            top = [e.text for e in labels if bbox.at_top(e)]
        if bottom is None:
            bottom = [e.text for e in labels if bbox.at_bottom(e)]
        if left is None:
            left = [e.text for e in labels if bbox.at_left(e)]
        if right is None:
            right = [e.text for e in labels if bbox.at_right(e)]

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
