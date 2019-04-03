import fault
from fault.verilog_utils import verilog_name


class SelectPath:
    def __init__(self, init=None):
        self.path = [] if init is None else init

    def insert(self, index, value):
        self.path.insert(index, value)

    def __getitem__(self, index):
        return self.path[index]

    # TODO: Do we want to support mutability?
    def __setitem__(self, index, value):
        self.path[index] = value

    def make_path(self, separator):
        path_str = ""
        # Skip outermost circuit definition (top) and innermost port
        # (appended next)
        for x in self.path[1:-1]:
            path_str += x.instance.name + separator
        if isinstance(self.path[-1], fault.WrappedVerilogInternalPort):
            path_str += self.path[-1].path
        else:
            path_str += verilog_name(self.path[-1].name)
        return path_str

    @property
    def system_verilog_path(self):
        return self.make_path(".")

    @property
    def verilator_path(self):
        return self.make_path("->")

    @property
    def debug_name(self):
        return self.make_path('.')

    def __len__(self):
        return len(self.path)
