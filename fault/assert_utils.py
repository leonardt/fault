from magma.bit import Bit
from magma.when import get_curr_block as get_curr_when_block, no_when


def add_compile_guards(compile_guard, verilog_str):
    if compile_guard is None:
        return verilog_str
    if not isinstance(compile_guard, (str, list)):
        raise TypeError("Expected string or list for compile_guard")
    if isinstance(compile_guard, str):
        compile_guard = [compile_guard]
    for guard in reversed(compile_guard):
        # Add tabs to line for indent
        nested_verilog_str = "\n    ".join(verilog_str.splitlines())
        verilog_str = f"""\
`ifdef {guard}
    {nested_verilog_str}
`endif
"""
    return verilog_str


def get_when_cond():
    """If active when cond, return a boolean that is true when the when
    condition is true.
    """
    if not get_curr_when_block():
        return None
    with no_when():
        when_cond = Bit()
        when_cond @= 0
    when_cond @= 1
    return when_cond
