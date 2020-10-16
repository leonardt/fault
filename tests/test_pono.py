import pytest
import coreir
import magma as m
import smt_switch as ss
from smt_switch.primops import (BVAdd, BVSub, BVMul, BVUdiv, Equal, Ite, Or,
                                Distinct)
import pono


class ConfigReg(m.Circuit):
    io = m.IO(D=m.In(m.Bits[2]), Q=m.Out(m.Bits[2])) + \
        m.ClockIO(has_ce=True)

    reg = m.Register(m.Bits[2], has_enable=True)(name="conf_reg")
    io.Q @= reg(io.D, CE=io.CE)


class SimpleALU(m.Circuit):
    io = m.IO(a=m.In(m.UInt[16]),
              b=m.In(m.UInt[16]),
              c=m.Out(m.UInt[16]),
              config_data=m.In(m.Bits[2]),
              config_en=m.In(m.Enable),
              ) + m.ClockIO()

    opcode = ConfigReg(name="config_reg")(io.config_data, CE=io.config_en)
    io.c @= m.mux([io.a + io.b, io.a - io.b, io.a * io.b, io.a / io.b], opcode)


@pytest.mark.parametrize('config_data', range(4))
def test_pono(config_data):
    # Compile magma -> coreir
    m.compile("build/SimpleALU", SimpleALU, output="coreir")

    # Load compile result
    context = coreir.Context()
    context.load_library("commonlib")
    top_mod = context.load_from_file("build/SimpleALU.json")

    # Create solver/interpolator
    solver = ss.create_msat_solver(False)
    itp = ss.create_msat_interpolator()

    # create RTS, populate with encoder
    rts = pono.RelationalTransitionSystem(solver)
    pono.CoreIREncoder(top_mod, rts)

    # create BV sorts
    bvsort16 = solver.make_sort(ss.sortkinds.BV, 16)
    bvsort2 = solver.make_sort(ss.sortkinds.BV, 2)

    # Reference to inputs
    a = rts.named_terms["a"]
    b = rts.named_terms["b"]

    # Make state var equal to output (result of the implementation)
    imp_res = rts.make_statevar('imp_res', bvsort16)
    rts.assign_next(imp_res, rts.named_terms["self.c"])

    # Create state var for spec result
    spec_res = rts.make_statevar('spec_res', bvsort16)

    # Expected op based on config_data param
    op = [BVAdd, BVSub, BVMul, BVUdiv][config_data]

    # Assign spec result to operation with a and b
    rts.assign_next(
        spec_res,
        solver.make_term(op, a, b)
    )

    # State machine variable
    test_state = rts.make_statevar('test_state', bvsort2)

    # Starts at state 0
    rts.constrain_init(solver.make_term(Equal, test_state,
                                        solver.make_term(0, bvsort2)))

    # sequential states 0 -> 1 -> 2 -> 3, then stays at 3
    rts.assign_next(
        test_state,
        solver.make_term(
            Ite,
            solver.make_term(
                Equal,
                test_state,
                solver.make_term(0, bvsort2)
            ),
            solver.make_term(1, bvsort2),
            solver.make_term(
                Ite,
                solver.make_term(
                    Equal,
                    test_state,
                    solver.make_term(1, bvsort2)
                ),
                solver.make_term(2, bvsort2),
                solver.make_term(
                    Ite,
                    solver.make_term(
                        Equal,
                        test_state,
                        solver.make_term(2, bvsort2)
                    ),
                    solver.make_term(3, bvsort2),
                    solver.make_term(3, bvsort2)
                )
            )
        )
    )

    # Boolean sort
    boolsort = solver.make_sort(ss.sortkinds.BOOL)

    # Create statevar to drive `config_en`
    config_en = rts.named_terms["config_en"]
    config_en_driver = rts.make_statevar('config_en_driver',
                                         boolsort)
    # Starts low
    rts.constrain_init(solver.make_term(Equal, config_en_driver,
                                        solver.make_term(False)))
    # Goes high for a cycle, then low for rest of states
    rts.assign_next(
        config_en_driver,
        solver.make_term(
            Ite,
            solver.make_term(
                Equal,
                test_state,
                solver.make_term(0, bvsort2)
            ),
            solver.make_term(True),
            solver.make_term(
                Ite,
                solver.make_term(
                    Equal,
                    test_state,
                    solver.make_term(1, bvsort2)
                ),
                solver.make_term(False),
                solver.make_term(
                    Ite,
                    solver.make_term(
                        Equal,
                        test_state,
                        solver.make_term(2, bvsort2)
                    ),
                    solver.make_term(False),
                    solver.make_term(False)
                )
            )
        )
    )
    # input and state var should be equal
    rts.add_constraint(
        solver.make_term(Equal, config_en, config_en_driver)
    )

    # config_data input is equal to config_data param
    rts.constrain_inputs(
        solver.make_term(Equal, rts.named_terms["config_data"],
                         solver.make_term(config_data, bvsort2))
    )

    # property imp_res matches spec_res when test_state == 3
    prop = pono.Property(
        rts, solver.make_term(Or, solver.make_term(Equal, imp_res, spec_res),
                              solver.make_term(Distinct, test_state,
                                               solver.make_term(3, bvsort2))))

    # set solver options
    solver.set_opt('produce-models', 'true')
    solver.set_opt('incremental', 'true')
    interp = pono.InterpolantMC(prop, solver, itp)
    assert interp.check_until(10)
