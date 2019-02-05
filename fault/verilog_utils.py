import magma as m


def verilog_name(name):
    if isinstance(name, m.ref.DefnRef):
        return str(name)
    if isinstance(name, m.ref.ArrayRef):
        array_name = verilog_name(name.array.name)
        return f"{array_name}_{name.index}"
    if isinstance(name, m.ref.TupleRef):
        tuple_name = verilog_name(name.tuple.name)
        return f"{tuple_name}_{name.index}"
    raise NotImplementedError(name, type(name))
