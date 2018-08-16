import fault.actions as actions


def verilator_cmd(top, verilog_filename, driver_filename, verilator_flags):
    DEFAULT_FLAGS = [
        "-Wall",
        "-Wno-INCABSPATH",
        "-Wno-DECLFILENAME"
    ]
    flags = DEFAULT_FLAGS
    flags.extend(verilator_flags)
    flag_str = " ".join(flags)
    return (f"verilator {flag_str} "
            f"--cc {verilog_filename} "
            f"--exe {driver_filename} "
            f"--top-module {top}")


def verilator_make_cmd(top):
    return f"make -C obj_dir -j -f V{top}.mk V{top}"
