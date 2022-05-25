from typing import Mapping

import magma as m
from fault.tester.synchronous import SynchronousTester
from fault.property import assert_, posedge


def wrap_with_sequence(ckt, sequences):
    class Wrapper(m.Circuit):
        io = m.IO(_fault_rv_tester_done_=m.Out(m.Bit))

        inst = ckt()

        # We lift non sequence ports as is, and sequence ports as monitors.
        normal_lifted = []
        monitors = []
        for key, value in ckt.interface.items():
            if key == "_fault_rv_tester_done_":
                raise RuntimeError("Reserved port name used")

            if key not in sequences:
                io += m.IO(**{key: value})
                normal_lifted.append(key)
            else:
                io += m.IO(**{key: m.Out(value)})
                monitors.append(key)

        for key in normal_lifted:
            m.wire(io[key], getattr(inst, key))

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
        io._fault_rv_tester_done_ @= done

        for key in monitors:
            value = getattr(inst, key)
            port = io[key]
            if m.is_producer(value):
                port.ready @= value.ready.value()
                port.valid @= value.valid
                port.data @= value.data
            else:
                port.ready @= value.ready
                port.valid @= value.valid.value()
                port.data @= value.data.value()
    return Wrapper


def _add_verilator_assert_flag(kwargs):
    # We need to include "-assert"  flat to the verilator command.
    if not kwargs:
        kwargs = {"flags": ["-assert"]}
    elif not kwargs.get("flags"):
        kwargs["flags"] = ["-assert"]
    elif "-assert" not in kwargs["flags"]:
        kwargs["flags"].append("-assert")
    return kwargs


def run_ready_valid_test(ckt: m.DefineCircuitKind, sequences: Mapping,
                         target, synthesizable: bool = True,
                         compile_and_run_args=[], compile_and_run_kwargs={}):
    if target == "verilator":
        compile_and_run_kwargs = \
            _add_verilator_assert_flag(compile_and_run_kwargs)
    if synthesizable:
        wrapped = wrap_with_sequence(ckt, sequences)
        tester = SynchronousTester(wrapped)
        tester.wait_until_high(wrapped._fault_rv_tester_done_, timeout=1000)
        tester.compile_and_run(target, *compile_and_run_args,
                               **compile_and_run_kwargs, disp_type="realtime")
        return
    raise NotImplementedError()


class ReadyValidTester(SynchronousTester):
    def __init__(self, ckt: m.DefineCircuitKind, sequences: Mapping,
                 *args, **kwargs):
        self.wrapped = wrap_with_sequence(ckt, sequences)
        super().__init__(self.wrapped, *args, **kwargs)

    def finish_sequences(self, timeout=1000):
        self.wait_until_high(self.wrapped._fault_rv_tester_done_,
                             timeout=timeout)

    def expect_sequences_finished(self):
        self.expect(self.wrapped._fault_rv_tester_done_, 1)

    def compile_and_run(self, target, *args, **kwargs):
        if target == "verilator":
            kwargs = _add_verilator_assert_flag(kwargs)
        super().compile_and_run(*args, **kwargs)
