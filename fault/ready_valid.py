from typing import Mapping

import magma as m
from fault.tester.staged_tester import Tester
from fault.property import assert_, posedge


def wrap_with_sequence(ckt, sequences):
    class Wrapper(m.Circuit):
        io = m.IO(done=m.Out(m.Bit)) + m.ClockIO()
        inst = ckt()
        done = m.Bit(1)
        for key, value in sequences.items():
            port = getattr(inst, key)
            n = len(value)
            # Counter to advance through sequence
            count = m.Register(m.UInt[(n - 1).bit_length()],
                               has_enable=True)()
            count.I @= count.O + 1

            # Current sequence elem chosen by counter
            curr = m.mux(value, count.O)

            # Still sequence elements to process
            not_done = (count.O != (n - 1))

            # NOTE: Here we could add logic for random stalls
            port_T = type(port)
            if m.is_consumer(port_T):
                # Advance count when circuit is ready and we are valid (not
                # done with sequence)
                count.CE @= not_done & port.ready
                port.data @= curr
                port.valid @= not_done
            elif m.is_producer(port_T):
                # Advance count when circuit produces valid and we are
                # ready (not done with sequence)
                count.CE @= not_done & port.valid
                port.ready @= not_done
                assert_(~(not_done & port.valid) | (port.data == curr),
                        on=posedge(io.CLK))
            else:
                raise NotImplementedError(port_T)
            # Done when all counters reach final element
            done = done & (count.O == (n - 1))
        io.done @= done
    return Wrapper


def run_ready_valid_test(ckt: m.DefineCircuitKind, sequences: Mapping,
                         target, synthesizable: bool = True,
                         compile_and_run_args=[], compile_and_run_kwargs={}):
    if target == "verilator":
        # Need assert flag for verilator
        if not compile_and_run_kwargs:
            compile_and_run_kwargs = {"flags": ["-assert"]}
        elif not compile_and_run_kwargs.get("flags"):
            compile_and_run_kwargs["flags"] = ["-assert"]
        elif "-assert" not in compile_and_run_kwargs["flags"]:
            compile_and_run_kwargs["flags"].append("-assert")
    if synthesizable:
        wrapped = wrap_with_sequence(ckt, sequences)
        tester = Tester(wrapped)
        tester.wait_until_high(wrapped.done, timeout=1000)
        tester.compile_and_run(target, *compile_and_run_args,
                               **compile_and_run_kwargs, disp_type="realtime")
        return
    raise NotImplementedError()
