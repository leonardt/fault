import os
os.environ["MANTLE_TARGET"] = "coreir"
import mantle
import fault

def ref_add(I0, I1, width):
    return I0 + I1


width = 16
@fault.test_case(combinational=True, random_strategy=fault.Uniform, num_tests=1)
def test_add_random(
        Add : mantle.DefineAdd(16),
        I0  : fault.Random(width),
        I1  : fault.Random(width)):
# def test_add_random(I0 : fault.Random(BitVector(width)), I1 : fault.Random(BitVector(width))):
    Add.I0 = I0
    Add.I1 = I1

    Add.eval()

    assert Add.O == ref_add(I0, I1, width)
    # assert Add.O == BitVector(Add.I0, 16) + BitVector(Add.I1, 16)

# def test_add_random():
#     Add = mantle.DefineAdd(16)
#
#     Add.I0 = fault.Random(width=16)
#     Add.I1 = fault.Random(width=16)
#
#     assert Add.O == BitVector(Add.I0, 16) + BitVector(Add.I1, 16)
