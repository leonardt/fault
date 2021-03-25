import fault
from fault.verilog_utils import verilog_name, verilator_name


class SelectPath:
    def __init__(self, init=None):
        self.path = [] if init is None else init

    @property
    def debug_name(self):
        assert hasattr(self.path[1], "debug_name"), type(self.path[-1])
        return self.path[-1].debug_name

    def insert(self, index, value):
        self.path.insert(index, value)

    def __getitem__(self, index):
        return self.path[index]

    # TODO: Do we want to support mutability?
    def __setitem__(self, index, value):
        self.path[index] = value

    def make_path(self, separator, name_func=verilog_name):
        # Initialize empty path
        path = []

        # Add the second through second-to-last entries to the path string.
        # Note that the first path entry is simply skipped.
        for x in self.path[1:-1]:
            if isinstance(x, str):
                path += [x]
            else:
                path += [x.instance.name]

        # Append the final path entry
        if isinstance(self.path[-1], fault.WrappedVerilogInternalPort):
            path += [self.path[-1].path]
        elif isinstance(self.path[-1], str):
            path += [self.path[-1]]
        else:
            path += [name_func(self.path[-1].name)]

        # Return the path string constructed with the provided separator.
        return separator.join(path)

    def system_verilog_path(self, disable_ndarray):
        def name_func(x):
            return verilog_name(x, disable_ndarray)
        return self.make_path(".",
                              name_func=name_func)

    @property
    def spice_path(self):
        return self.make_path(".")

    @property
    def verilator_path(self):
        return self.make_path("->", name_func=verilator_name)

    @property
    def debug_name(self):
        return self.make_path('.')

    def __len__(self):
        return len(self.path)
