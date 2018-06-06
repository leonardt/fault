import fault as f

one_bit_comp_io = {
    "io16in_in_arg_1_0_0": {
        "bits": {
            "0": "pad_S2_T15",
            "1": "pad_S2_T14",
            "2": "pad_S2_T13",
            "3": "pad_S2_T12",
            "4": "pad_S2_T11",
            "5": "pad_S2_T10",
            "6": "pad_S2_T9",
            "7": "pad_S2_T8",
            "8": "pad_S2_T7",
            "9": "pad_S2_T6",
            "10": "pad_S2_T5",
            "11": "pad_S2_T4",
            "12": "pad_S2_T3",
            "13": "pad_S2_T2",
            "14": "pad_S2_T1",
            "15": "pad_S2_T0"
        },
        "mode": "in",
        "width": 16
    },
    "io1_out_0_0": {
        "bits": {
            "15": "pad_S0_T0"
        },
        "mode": "out",
        "width": 1
    }
}

IO = {
    "in": {},
    "out": {}
}

for key, value in one_bit_comp_io:
    IO[value["mode"]][key] = value

DATA_WIDTH = 16
@fault.test_case
def test_cgra(# Every input/output has the same name for Halide programs
              input_image  : f.File("io16in_in_arg_1_0_0", "rb"),
              bitstream    : f.File("pointwise.bs", "r"),
              output_image : f.File("io1_out_0_0", "wb"),
              CGRA         : m.DefineCGRA(16, 16)):
    input_byte = input_image.read(1)

    CGRA.clk_in = 0
    CGRA.reset_in = 0
    CGRA.config_addr = 0
    CGRA.config_data = 0

    CGRA.eval()

    # Reset the chip
    CGRA.reset_in = 1
    CGRA.eval()
    CGRA.reset_in = 0
    CGRA.eval()

    CGRA.advance()

    for line in bitstream:
        CGRA.config_addr, CGRA.config_data = line.split()
        CGRA.advance(2)

    while input_byte: # returns b”” at the end, which evaluates to False
        # TODO: Use macro to metaprogram this
        # vim macro to do this, beginning on first line, first column
        # qa yyp f_;ll<C-x> f]h<C-a>_ q 14@a
        # TODO: Record a vim macro and generate a metaprogram
        # CGRA.pad_S0_T15 = input_byte[0]
        # CGRA.pad_S0_T14 = input_byte[1]
        # CGRA.pad_S0_T13 = input_byte[2]
        # CGRA.pad_S0_T12 = input_byte[3]
        # CGRA.pad_S0_T11 = input_byte[4]
        # CGRA.pad_S0_T10 = input_byte[5]
        # CGRA.pad_S0_T9 = input_byte[6]
        # CGRA.pad_S0_T8 = input_byte[7]
        # CGRA.pad_S0_T7 = input_byte[8]
        # CGRA.pad_S0_T6 = input_byte[9]
        # CGRA.pad_S0_T5 = input_byte[10]
        # CGRA.pad_S0_T4 = input_byte[11]
        # CGRA.pad_S0_T3 = input_byte[12]
        # CGRA.pad_S0_T2 = input_byte[13]
        # CGRA.pad_S0_T1 = input_byte[14]
        # CGRA.pad_S0_T0 = input_byte[15]
        for i in range(0, DATA_WIDTH):
            setattr(CGRA, f"pad_s0_T{i}", input_byte[i])

        CGRA.advance()

        output_byte = f.Byte()

        for i in range(0, DATA_WIDTH):
            output_byte[i] = getattr(CGRA, f"pad_s2_T{i}")
        output_image.write(output_byte)

        CGRA.advance()

        input_byte = input_image.read(1)
