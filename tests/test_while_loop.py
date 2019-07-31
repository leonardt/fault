import pathlib
import tempfile
import fault
import magma as m
import os
import shutil
import logging
import mantle


def pytest_generate_tests(metafunc):
    if 'target' in metafunc.fixturenames:
        targets = []
        if shutil.which('vcs'):
            targets.append(('system-verilog', 'vcs'))
        if shutil.which('ncsim'):
            targets.append(('system-verilog', 'ncsim'))
        if shutil.which('iverilog'):
            targets.append(('system-verilog', 'iverilog'))
        metafunc.parametrize('target,simulator', targets)


def debug_print(tester, dut):
    to_display = {
            'dut.n_done': dut.n_done,
            'dut.count': dut.count
    }

    args = []
    fmt = []
    for key, val in to_display.items():
        args.append(val)
        fmt.append(f'{key}: %0d')

    tester.print(', '.join(fmt) + '\n', *args)


def test_def_vlog(target, simulator, n_cyc=3, n_bits=8):
    logging.getLogger().setLevel(logging.DEBUG)

    dut_fname = pathlib.Path('tests/verilog/clkdelay.sv').resolve()
    dut = m.DeclareCircuit('clkdelay', 
                           'clk', m.In(m.Clock),
                           'rst', m.In(m.Bit),
                           'count', m.Out(m.Bits[n_bits]),
                           'n_done', m.Out(m.Bit))

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
    tester.expect(dut.count, n_cyc-1)
    tester.expect(dut.n_done, 0)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)

    # run the test
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(
            target=target,
            simulator=simulator,
            directory=tmp_dir,
            ext_libs=[dut_fname],
            sim_env=sim_env,
            skip_compile=True,
            ext_model_file=True,
            defines={'N_CYC': n_cyc, 'N_BITS': n_bits}
        )
