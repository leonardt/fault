import magma as m


def assert_immediate(cond, success_msg=None, error_msg=None, severity="error",
                     on="*"):
    """
    cond: m.Bit
    success_msg (optional): passed to $display on success
    error_msg (optional): passed to else $<severity> on failure
    severity (optional): "error", "fatal", or "warning"
    """
    success_msg_str = ""
    if success_msg is not None:
        success_msg_str = f" $display(\"{success_msg}\")"
    error_msg_str = ""
    if error_msg is not None:
        error_msg_str = f" else ${severity}(\"{error_msg}\")"
    m.inline_verilog(f"""\
always @({on}) begin
    assert ({cond}){success_msg_str}{error_msg_str};
end""")
