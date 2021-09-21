import magma as m
from fault.tester.staged_tester import Tester
from fault.assert_immediate import assert_immediate


class ReadyValidTester:
    def __init__(self, circuit: m.Circuit, sequences: dict):
        class Wrapper(m.Circuit):
            io = m.IO(done=m.Out(m.Bit))
            inst = circuit()
            done = m.Bit(1)
            for key, value in sequences.items():
                port = getattr(inst, key)
                n = len(value)
                count = m.Register(m.UInt[(n - 1).bit_length()],
                                   has_enable=True)()
                # NOTE: Here we can add logic for random stalls
                count.I @= count.O + 1
                curr = m.mux(value, count.O)
                not_done = (count.O != (n - 1))

                port_T = type(port)
                if port_T.is_consumer():
                    count.CE @= not_done & port.ready
                    port.data @= curr
                    port.valid @= not_done
                elif port_T.is_producer():
                    count.CE @= not_done & port.valid
                    port.ready @= not_done
                    assert_immediate(~(not_done & port.valid) |
                                     (port.data == curr))
                else:
                    raise NotImplementedError(port_T)
                done = done & (count.O == (n - 1))
            io.done @= done

        self.circuit = Wrapper

    def compile_and_run(self, *args, **kwargs):
        tester = Tester(self.circuit)
        tester.wait_until_high(self.circuit.done)
        tester.compile_and_run(*args, **kwargs)
