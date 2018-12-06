import magma
import fault.actions as actions


def verilator_cmd(top, verilog_filename, include_verilog_libraries,
                  include_directories, driver_filename, verilator_flags):
    DEFAULT_FLAGS = [
        "-Wall",
        "-Wno-INCABSPATH",
        "-Wno-DECLFILENAME"
    ]
    flags = DEFAULT_FLAGS
    flags.extend(verilator_flags)
    flag_str = " ".join(flags)
    include_str = ' '.join(f'-v {file_}' for file_ in include_verilog_libraries)
    if include_directories:
        include_str += " " + " ".join(f"-I{dir_}" for dir_ in
                                      include_directories)
    return (f"verilator {flag_str} "
            f"--cc {verilog_filename} "
            f"{include_str} "
            f"--exe {driver_filename} "
            f"--top-module {top}")


def verilator_make_cmd(top):
    return f"make -C obj_dir -j -f V{top}.mk V{top}"
