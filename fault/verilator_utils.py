import magma
import fault.actions as actions


def verilator_cmd(top, verilog_filename, include_verilog_files, driver_filename,
                  verilator_flags):
    DEFAULT_FLAGS = [
        "-Wall",
        "-Wno-INCABSPATH",
        "-Wno-DECLFILENAME"
    ]
    flags = DEFAULT_FLAGS
    flags.extend(verilator_flags)
    flag_str = " ".join(flags)
    include_str = ' '.join(f'-v {file_}' for file_ in include_verilog_files)
    return (f"verilator {flag_str} "
            f"--cc {verilog_filename} "
            f"{include_str} "
            f"--exe {driver_filename} "
            f"--top-module {top}")


def verilator_make_cmd(top):
    return f"make -C obj_dir -j -f V{top}.mk V{top}"


def verilator_name(name):
    if isinstance(name, magma.ref.DefnRef):
        return str(name)
    if isinstance(name, magma.ref.ArrayRef):
        array_name = verilator_name(name.array.name)
        return f"{array_name}_{name.index}"
    raise NotImplementedError(name, type(name))
