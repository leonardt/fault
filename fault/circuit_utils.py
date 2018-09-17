def check_interface_is_subset(circuit1, circuit2):
    """
    Checks that the interface of circuit1 is a subset of circuit2

    Subset is defined as circuit2 contains all the ports of circuit1. Ports are
    matched by name comparison, then the types are checked to see if one could
    be converted to another.
    """
    circuit1_port_names = circuit1.interface.ports.keys()
    for name in circuit1_port_names:
        if name not in circuit2.interface.ports:
            raise ValueError(f"{circuit2} (circuit2) does not have port {name}")
        circuit1_kind = type(type(getattr(circuit1, name)))
        circuit2_kind = type(type(getattr(circuit2, name)))
        # Check that the type of one could be converted to the other
        if not (issubclass(circuit2_kind, circuit1_kind) or
                issubclass(circuit1_kind, circuit2_kind)):
            raise ValueError(f"Port {name} types don't match:"
                             f" Type0={circuit1_kind},"
                             f" Type1={circuit2_kind}")
