from fault.verilog_target import verilog_name


class SelectPath:
    def __init__(self, init=None):
        self.path = [] if init is None else init

    def insert(self, index, value):
        self.path.insert(index, value)

    def __getitem__(self, index):
        return self.path[index]

    @property
    def verilator_path(self):
        path_str = ""
        # Skip outermost circuit definition (top) and innermost port
        # (appended next)
        for x in self.path[1:-1]:
            path_str += x.instance.name + "->"
        path_str += verilog_name(self.path[-1].name)
        return path_str
