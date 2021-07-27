import magma as m
from fault.property import Posedge
from fault.assert_utils import add_compile_guards


def _make_assert(type_, cond, success_msg=None, failure_msg=None,
                 severity="error", name=None, compile_guard=None, delay=False,
                 inline_wire_prefix=None):
    if inline_wire_prefix is None:
        inline_wire_prefix = "_FAULT_ASSERT_WIRE_"
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
    name_str = "" if name is None else f"{name}: "
    delay_str = "" if not delay else "#1"
    assert_str = """\
{type_} begin
{delay_str}
{name_str}assert ({cond}){success_msg_str}{failure_msg_str};
end
"""
    assert_str = add_compile_guards(compile_guard, assert_str)
    m.inline_verilog(
        assert_str, inline_wire_prefix=inline_wire_prefix,
        **format_args, type_=type_)


def _add_docstr(fn):
    # The three assert_* variants share the same interface, so we use a simple
    # decorator to reapply the docstring to each rather than repeating the
    # string in each function
    fn.__doc__ = """
    cond: m.Bit
    success_msg (optional): passed to $display on success
    failure_msg (optional): passed to else $<severity> on failure (strings are
                            wrapped in quotes, integers are passed without
                            quotes (for $fatal)), can also pass a tuple of the
                            form  `("<display message>", *display_args)` to
                            display debug information upon failure
    severity (optional): "error", "fatal", or "warning"
    name (optional): Adds `{name}: ` prefix to assertion
    compile_guard (optional): a string or list of strings corresponding to
                              macro variables used to guard the assertion with
                              verilog `ifdef statements
    """
    return fn


@_add_docstr
def assert_immediate(cond, success_msg=None, failure_msg=None, severity="error",
                     name=None, compile_guard=None, inline_wire_prefix=None):
    _make_assert("always @(*)", cond, success_msg, failure_msg, severity, name,
                 compile_guard, inline_wire_prefix=inline_wire_prefix)


@_add_docstr
def assert_final(cond, success_msg=None, failure_msg=None, severity="error",
                 name=None, compile_guard=None, inline_wire_prefix=None):
    _make_assert("final", cond, success_msg, failure_msg, severity, name,
                 compile_guard, inline_wire_prefix=inline_wire_prefix)


@_add_docstr
def assert_initial(cond, success_msg=None, failure_msg=None, severity="error",
                   name=None, compile_guard=None, inline_wire_prefix=None):
    _make_assert("initial", cond, success_msg, failure_msg, severity, name,
                 compile_guard, delay=True,
                 inline_wire_prefix=inline_wire_prefix)
