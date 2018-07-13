import magma
import mantle
import fault

@fault.test_case(combinational=True, random_strategy=Uniform, num_tests=256)
def test_add():
    Add = mantle.DefineAdd(16)

    Add.I0 = fault.Random(width=16)
    Add.I1 = fault.Random(width=16)

    with fault.constraints:
        Add.I0.popcount() > 5

    assert Add.O == BitVector(Add.I0, 16) + BitVector(Add.I1, 16)


def check_memory_address(memory, adddr, expected):
    memory.raddr = addr
    memory.ren = 1
    step(memory)
    assert memory.rdata == expected

@fault.test_case
def test_memory():
    memory = mantle.DefineRAM(height=16, width=16)

    expected = {}
    for i in range(16):
        addr = BitVector(i, 4)
        data = fault.Random(width=16)
        expected[addr] = data
        memory.wdata = data
        memory.waddr = addr
        memory.wen = 1
        step(memory)
        memory.wen = 0

        check_memory_address(memory, addr, data)

    for addr, data in expected.items():
        check_memory_address(memory, addr, data)
