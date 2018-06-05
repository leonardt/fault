import os
os.environ["MANTLE_TARGET"] = "coreir"
import magma as m
import mantle
import fault

def ref_add(I0, I1, width):
    return I0 + I1


# def test_add_random(I0 : fault.Random(BitVector(width)), I1 : fault.Random(BitVector(width))):
width = 16
@fault.test_case(combinational=True, random_strategy=fault.Uniform, num_tests=1)
def test_add_random(Add : mantle.DefineAdd(16),
                    I0  : fault.Random(width),
                    I1  : fault.Random(width)):
#     Add = mantle.DefineAdd(16)
#
#     Add.I0 = fault.Random(width=16)
#     Add.I1 = fault.Random(width=16)
    Add.I0 = I0
    Add.I1 = I1

    Add.eval()

    assert Add.O == ref_add(I0, I1, width)
    # assert Add.O == BitVector(Add.I0, 16) + BitVector(Add.I1, 16)

class TFF(m.Circuit):
    name = "TFF"
    IO = ["O", m.Out(m.Bit)] + m.ClockInterface()
    @classmethod
    def definition(cls):
        # instance a dff to hold the state of the toggle flip-flop - this needs to be done first
        ff = mantle.DFF()

        # compute the next state as the not of the old state ff.O
        ff( ~ff.O )
        m.wire(ff.O, cls.O)

@fault.test_case
def test_tff(TFF : TFF):
    TFF.eval()
    for i in range(0, 8):
        assert TFF.O == i % 2
        TFF.next()
