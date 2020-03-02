class WrappedVerilogInternalPort:
    def __init__(self, path: str, type_):
        """
        path: <instance_name>.<port_name> (can nest instances)

        type_: magma type of the signal (e.g. m.Bits(2))
        """
        self.path = path
        self.type_ = type_
