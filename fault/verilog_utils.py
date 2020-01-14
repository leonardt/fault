import magma as m


def verilog_name(name, is_imported_verilog_circuit):
    if isinstance(name, m.ref.DefnRef):
        return str(name)
    if isinstance(name, m.ref.ArrayRef):
        array_name = verilog_name(name.array.name, is_imported_verilog_circuit)
        if issubclass(name.array.T, m.Digital):
            return f"{array_name}[{name.index}]"
        T = type(name.array)
        # Handle packed n-d arrays for imported verilog
        if issubclass(T, m.Array) and not issubclass(T.T, m.Digital):
            while not issubclass(T, m.Digital) and \
                    is_imported_verilog_circuit:
                T = T.T
            # Don't flatten if imported verilog and n-d array of bits
            if issubclass(T, m.Digital) and \
                    is_imported_verilog_circuit:
                return f"{array_name}[{name.index}]"
        return f"{array_name}_{name.index}"
    if isinstance(name, m.ref.TupleRef):
        tuple_name = verilog_name(name.tuple.name, is_imported_verilog_circuit)
        index = name.index
        try:
            int(index)
            # python/coreir don't allow pure integer names
            index = f"_{index}"
        except ValueError:
            pass
        return f"{tuple_name}_{index}"
    raise NotImplementedError(name, type(name))


def verilator_name(name, is_imported_verilog_circuit):
    if isinstance(name, m.ref.ArrayRef) and issubclass(name.array.T, m.Digital):
        # Setting a specific bit is done using bit twiddling, so we return the
        # full array see https://github.com/leonardt/fault/pull/194 for more
        # info
        name = verilog_name(name.array.name, is_imported_verilog_circuit)
    else:
        name = verilog_name(name, is_imported_verilog_circuit)
    # pg 21 of verilator 4.018 manual
    # To avoid conicts with Verilator's internal symbols, any double
    # underscore are replaced with ___05F (5F is the hex code of an underscore.)
    return name.replace("__", "___05F")
