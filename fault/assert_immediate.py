import magma as m
from fault.property import Posedge


def assert_immediate(cond, success_msg=None, failure_msg=None, severity="error",
                     on=None, name=None):
    """
    cond: m.Bit
    success_msg (optional): passed to $display on success
    failure_msg (optional): passed to else $<severity> on failure (strings are
                            wrapped in quotes, integers are passed without
                            quotes (for $fatal)), can also pass a tuple of the
                            form  `("<display message>", *display_args)` to 
                            display debug information upon failure
    severity (optional): "error", "fatal", or "warning"
    on (optional): If None, uses always @(*) sensitivity, otherwise something
                   like f.posedge(io.CLK)
    name (optional): Adds `{name}: ` prefix to assertion
    """
    success_msg_str = ""
    if success_msg is not None:
        success_msg_str = f" $display(\"{success_msg}\");"
    failure_msg_str = ""
    format_args = {}
    if failure_msg is not None:
        if isinstance(failure_msg, str):
            failure_msg = f"\"{failure_msg}\""
        elif isinstance(failure_msg, int):
            failure_msg = str(failure_msg)
        elif isinstance(failure_msg, tuple):
            msg, *args = failure_msg
            failure_msg = f"\"{msg}\""
            for i in range(len(args)):
                failure_msg += f", {{_fault_assert_immediate_arg_{i}}}"
                format_args[f"_fault_assert_immediate_arg_{i}"] = args[i]
        else:
            raise TypeError(
                f"Unexpected type for failure_msg={type(failure_msg)}")
        failure_msg_str = f" else ${severity}({failure_msg});"
    if on is None:
        on = "@(*)"
    elif isinstance(on, Posedge):
        on = on.compile(format_args)
    else:
        raise TypeError(f"Unexpected type for on={type(on)}")
    name_str = "" if name is None else f"{name}: "
    m.inline_verilog(
        "always {on} {name_str}assert ({cond})"
        "{success_msg_str}{failure_msg_str};",
        **format_args)
