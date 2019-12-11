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


# @pytest.mark.skipif(not shutil.which("irun"), reason="irun not available")
@pytest.mark.skipif(True)
def test_load_runtime():
    # define an empty circuit
    mod = kratos.Generator("mod")
    with tempfile.TemporaryDirectory() as temp:
        finish_file = os.path.join(temp, "finish")

        def run_test():
            # -g without the db dump
            circuit = kratos.util.to_magma(mod, insert_debug_info=True)
            tester = fault.Tester(circuit)
            tester.compile_and_run(target="system-verilog",
                                   simulator="ncsim",
                                   directory=temp,
                                   magma_output="verilog",
                                   use_kratos=True)
            # touch a file
            pathlib.Path(finish_file).touch(exist_ok=True)
        # run it in a separate process to fake a debugger-simulator interaction
        p = multiprocessing.Process(target=run_test)
        p.start()
        # wait for 1 second, which should be enough
        time.sleep(5)
        # send an CONTINUE request to the runtime to check if it's working
        from kratos_runtime import DebuggerMock
        mock = DebuggerMock()
        mock.continue_()
        # 1 second time out
        p.join(timeout=1)
        assert os.path.isfile(finish_file), "Unable to continue the simulation"
        os.remove(finish_file)
