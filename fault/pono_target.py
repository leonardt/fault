import coreir
import smt_switch as ss
from smt_switch.primops import BVAdd, Equal, Ite, Implies
import pono
import magma as m
from .verilog_utils import verilog_name
from fault.select_path import SelectPath
from fault.verilog_target import VerilogTarget
from pathlib import Path


def get_width(port):
    if isinstance(port, m.Digital):
        return None
    return len(port)


class PonoTarget(VerilogTarget):
    def __init__(self, circuit, directory="build/", skip_compile=False,
                 include_verilog_libraries=[], magma_output="coreir-verilog",
                 circuit_name=None, magma_opts={}, solver="btor"):
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         include_verilog_libraries, magma_output, magma_opts)
        self.state_index = 0
        self.curr_state_pokes = []
        self.step_offset = 0
        self.pokes = {}
        self.solver = solver

    def compile_expression(self, value):
        raise NotImplementedError()

    def make_eval(self, i, action):
        raise NotImplementedError()

    def make_expect(self, i, action):
        raise NotImplementedError()

    def make_poke(self, i, action):
        name = verilog_name(action.port.name)
        value = action.value
        width = get_width(action.port)
        # TODO: type check width?
        key = (name, width)
        if key not in self.pokes:
            self.pokes[key] = {}
        self.pokes[key][self.state_index] = value

    def make_print(self, i, action):
        raise NotImplementedError()

    def make_loop(self, i, action):
        raise NotImplementedError()

    def make_file_open(self, i, action):
        raise NotImplementedError()

    def make_file_close(self, i, action):
        raise NotImplementedError()

    def make_file_read(self, i, action):
        raise NotImplementedError()

    def make_file_write(self, i, action):
        raise NotImplementedError()

    def make_file_scan_format(self, i, action):
        raise NotImplementedError()

    def make_var(self, i, action):
        raise NotImplementedError()

    def make_delay(self, i, action):
        raise NotImplementedError()

    def make_get_value(self, i, action):
        raise NotImplementedError()

    def make_assert(self, i, action):
        raise NotImplementedError()

    def make_if(self, i, action):
        raise NotImplementedError()

    def make_while(self, i, action):
        raise NotImplementedError()

    def make_join(self, i, action):
        raise NotImplementedError()

    def make_step(self, i, action):
        if action.steps > 2:
            # Only supports 1 cycle per state
            raise NotImplementedError()
        self.step_offset += action.steps
        if self.step_offset % 2 == 0:
            for port, pokes in self.pokes.items():
                if len(pokes) < self.state_index + 1:
                    assert len(pokes) == self.state_index
                    prev_value = pokes[self.state_index - 1]
                    pokes[self.state_index] = prev_value
            self.state_index += 1

    def add_assumptions(self, solver, rts, ports):
        for assumption in self.assumptions:
            port = assumption.port
            if isinstance(port, SelectPath):
                name = port.verilator_path
                width = get_width(port[-1])
            else:
                name = verilog_name(port.name)
                width = get_width(port)
            if width is None:
                sort = solver.make_sort(ss.sortkinds.BOOL)
            else:
                sort = solver.make_sort(ss.sortkinds.BV, width)
            rts.constrain_inputs(assumption.value(solver, ports[name], sort))

    def process_guarantees(self, solver, rts, at_end_state_flag, ports):
        for i, guarantee in enumerate(self.guarantees):
            prop = pono.Property(
                rts,
                solver.make_term(
                    Implies,
                    at_end_state_flag,
                    guarantee.value(solver, ports)
                )
            )
            interp = pono.KInduction(prop, solver)
            assert interp.check_until(10), interp.witness()

    def generate_code(self, actions, solver, rts, ports):
        for i, action in enumerate(actions):
            self.generate_action_code(i, action)

        # State machine variable
        n = self.state_index - 1
        state_sort = solver.make_sort(ss.sortkinds.BV,
                                      n.bit_length())
        test_state = rts.make_statevar(
            'test_state', state_sort)

        # Starts at state 0
        rts.constrain_init(solver.make_term(Equal, test_state,
                                            solver.make_term(0, state_sort)))

        # sequential states 0 -> 1 -> 2 -> ... -> n, then stays at n
        # TODO: Assumes sequential states
        n = solver.make_term(n, state_sort)
        rts.assign_next(
            test_state,
            solver.make_term(
                Ite,
                solver.make_term(Equal, test_state, n),
                n,
                solver.make_term(BVAdd, test_state,
                                 solver.make_term(1, state_sort))))
        for (name, width), values in self.pokes.items():
            print(name, values)
            if name == "CLK":
                # Ignore clocks since they're abstracted
                # TODO: Should verify the behavior is the same as constrained
                # random backend
                continue
            if width is None:
                sort = solver.make_sort(ss.sortkinds.BOOL)
            else:
                sort = solver.make_sort(ss.sortkinds.BV, width)
            var = rts.make_statevar(f"{name}_driver", sort)

            def _make_value(value):
                if width is None:
                    return solver.make_term(bool(value))
                return solver.make_term(int(value), sort)

            rts.constrain_init(solver.make_term(Equal, var,
                                                _make_value(values[0])))

            var_next = _make_value(values[len(values) - 1])
            for i, value in reversed(list(values.items())[:-1]):
                var_next = solver.make_term(
                    Ite,
                    solver.make_term(Equal, test_state,
                                     solver.make_term(i, state_sort)),
                    _make_value(value),
                    var_next
                )
            rts.assign_next(var, var_next)
            # driver and state var should be equal
            rts.add_constraint(
                solver.make_term(Equal, var, rts.named_terms[name])
            )
        self.add_assumptions(solver, rts, ports)
        at_end_state_flag = solver.make_term(Equal, test_state, n)
        return at_end_state_flag

    def run(self, actions):
        # Create solver/interpolator
        solver = ss.create_btor_solver(False)

        # set solver options
        solver.set_opt('produce-models', 'true')
        solver.set_opt('incremental', 'true')

        # Load compile result
        context = coreir.Context()
        context.load_library("commonlib")
        top_mod = context.load_from_file(str(self.directory /
                                             Path(f"{self.circuit_name}.json")))

        rts = pono.RelationalTransitionSystem(solver)
        pono.CoreIREncoder(top_mod, rts)
        ports = {}
        for name, port in self.circuit.interface.ports.items():
            if name == "CLK":
                continue
            width = get_width(port)
            if width is None:
                sort = solver.make_sort(ss.sortkinds.BOOL)
            else:
                sort = solver.make_sort(ss.sortkinds.BV, width)
            if port.is_input():
                ports[name] = rts.make_statevar(f"{name}_out", sort)
                rts.assign_next(ports[name], rts.named_terms[f"self.{name}"])
            else:
                ports[name] = rts.make_statevar(f"{name}_in", sort)
                rts.assign_next(ports[name], rts.named_terms[name])
                rts.constrain_inputs(
                    solver.make_term(Equal, rts.named_terms[name],
                                     ports[name]))

        at_end_state_flag = self.generate_code(actions, solver, rts, ports)
        self.process_guarantees(solver, rts, at_end_state_flag, ports)
