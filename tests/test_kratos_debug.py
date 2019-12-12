import fault
import pytest
import kratos
import multiprocessing
import time
import pathlib
import tempfile
import os
import magma
import shutil

try:
    import kratos_runtime
    has_runtime = True
except ImportError:
    has_runtime = False


@pytest.mark.skipif((not shutil.which("irun")) and not has_runtime,
                    reason="irun not available")
def test_load_runtime():
    # define an empty circuit
    mod = kratos.Generator("mod")
    with tempfile.TemporaryDirectory() as temp:

        def run_test():
            # -g without the db dump
            circuit = kratos.util.to_magma(mod, insert_debug_info=True)
            tester = fault.Tester(circuit)
            tester.compile_and_run(target="system-verilog",
                                   simulator="ncsim",
                                   directory=temp,
                                   magma_output="verilog",
                                   use_kratos=True)
        # run it in a separate process to fake a debugger-simulator interaction
        p = multiprocessing.Process(target=run_test)
        p.start()
        # send an CONTINUE request to the runtime to check if it's working
        from kratos_runtime import DebuggerMock
        mock = DebuggerMock()
        time.sleep(1)
        mock.connect()
        mock.continue_()
        mock.wait_till_finish()
        p.join()


@pytest.mark.skipif(not has_runtime, reason="runtime not available")
def test_veriltor_load():
    # define an empty circuit
    mod = kratos.Generator("mod")
    with tempfile.TemporaryDirectory() as temp:

        def run_test():
            # -g without the db dump
            circuit = kratos.util.to_magma(mod, insert_debug_info=True)
            tester = fault.Tester(circuit)
            tester.compile_and_run(target="verilator",
                                   directory=temp,
                                   disp_type="realtime",
                                   magma_output="verilog",
                                   use_kratos=True)
        # run it in a separate process to fake a debugger-simulator interaction
        p = multiprocessing.Process(target=run_test)
        p.start()
        # send an CONTINUE request to the runtime to check if it's working
        from kratos_runtime import DebuggerMock
        mock = DebuggerMock()
        time.sleep(1)
        mock.connect()
        mock.continue_()
        mock.wait_till_finish()
        p.join()
