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
