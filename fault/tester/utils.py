from ..select_path import SelectPath
from ..wrapped_internal_port import WrappedVerilogInternalPort


def get_port_type(port):
    if isinstance(port, SelectPath):
        port = port[-1]
    if isinstance(port, WrappedVerilogInternalPort):
        return port.type_
    return type(port)
