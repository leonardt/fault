from pathlib import Path
import fault
import magma as m


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'system-verilog')


def debug_print(tester, dut):
    to_display = {'dut.n_done': dut.n_done, 'dut.count': dut.count}

    args = []
    fmt = []
    for key, val in to_display.items():
        args.append(val)
        fmt.append(f'{key}: %0d')

    tester.print(', '.join(fmt) + '\n', *args)


def test_while_loop(target, simulator, n_cyc=3, n_bits=8):
    dut = m.DeclareCircuit('clkdelay',
                           'clk', m.In(m.Clock),
                           'rst', m.In(m.Bit),
                           'count', m.Out(m.Bits[n_bits]),
                           'n_done', m.Out(m.Bit))

    # instantiate the tester
    tester = fault.Tester(dut, dut.clk)

    # reset
    tester.poke(dut.rst, 1)
    tester.poke(dut.clk, 0)
    tester.step()
    tester.step()

    # check initial state
    tester.expect(dut.n_done, 1)
    tester.expect(dut.count, 0)

    # wait for the loop to complete
    tester.poke(dut.rst, 0)
    loop = tester._while(dut.n_done)
    debug_print(loop, dut)
    loop.step()
    loop.step()

    debug_print(tester, dut)

    # check final state
    tester.expect(dut.count, n_cyc - 1)
    tester.expect(dut.n_done, 0)

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        tmp_dir=True,
        ext_libs=[Path('tests/verilog/clkdelay.sv').resolve()],
        ext_model_file=True,
        defines={'N_CYC': n_cyc, 'N_BITS': n_bits}
    )
