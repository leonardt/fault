import fault
import pytest
import kratos
import multiprocessing
import time
import tempfile
import magma as m
import shutil
import operator
import hwtypes


has_runtime = fault.util.has_kratos_runtime()


def mock_debugger(fn):
    # run it in a separate process to fake a debugger-simulator interaction
    p = multiprocessing.Process(target=fn)
    p.start()
    # send an CONTINUE request to the runtime to check if it's working
    from kratos_runtime import DebuggerMock
    mock = DebuggerMock()
    time.sleep(1)
    mock.connect()
    mock.continue_()
    mock.wait_till_finish()
    p.join()


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
        mock_debugger(run_test)


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
                                   magma_output="verilog",
                                   use_kratos=True)
        mock_debugger(run_test)


# TODO: move the function in magma as a normal library call
def build_kratos_debug_info(circuit, is_top):
    inst_to_defn_map = {}
    for instance in circuit.instances:
        instance_inst_to_defn_map = \
            build_kratos_debug_info(type(instance), is_top=False)
        for k, v in instance_inst_to_defn_map.values():
            key = instance.name + "." + k
            if is_top:
                key = circuit.name + "." + key
            inst_to_defn_map[key] = v
        inst_name = instance.name
        if is_top:
            inst_name = circuit.name + "." + instance.name
        if instance.kratos is not None:
            inst_to_defn_map[inst_name] = instance.kratos
    return inst_to_defn_map


@pytest.mark.skipif(not has_runtime, reason="runtime not available")
@pytest.mark.parametrize("target", ["verilator", "system-verilog"])
def test_magma_debug(target):
    if not shutil.which("irun"):
        pytest.skip("irun not available")

    @m.circuit.combinational_to_verilog(debug=True)
    def execute_alu(a: m.UInt[16], b: m.UInt[16], config_: m.Bits[2]) -> \
            m.UInt[16]:
        if config_ == m.bits(0, 2):
            c = a + b
        elif config_ == m.bits(1, 2):
            c = a - b
        elif config_ == m.bits(2, 2):
            c = a * b
        else:
            c = m.bits(0, 16)
        return c

    class SimpleALU(m.Circuit):
        io = m.IO(a=m.In(m.UInt[16]), b=m.In(m.UInt[16]),
                  c=m.Out(m.UInt[16]), config_=m.In(m.Bits[2]))

        io.c <= execute_alu(io.a, io.b, io.config_)

    inst_to_defn_map = build_kratos_debug_info(SimpleALU, is_top=True)
    assert "SimpleALU.execute_alu_inst0" in inst_to_defn_map
    generators = []
    for instance_name, mod in inst_to_defn_map.items():
        mod.instance_name = instance_name
        generators.append(mod)

    tester = fault.Tester(SimpleALU)
    ops = [operator.add, operator.sub, operator.mul, operator.floordiv]
    for i, op in enumerate(ops):
        tester.circuit.config_ = i
        tester.circuit.a = a = hwtypes.BitVector.random(16)
        tester.circuit.b = b = hwtypes.BitVector.random(16)
        tester.eval()
        if op == operator.floordiv:
            tester.circuit.c.expect(0)
        else:
            tester.circuit.c.expect(op(a, b))

    with tempfile.TemporaryDirectory() as temp:

        def run_test():
            kwargs = {"target": target, "directory": temp,
                      "magma_output": "verilog",
                      "use_kratos": True}
            if target == "system-verilog":
                kwargs["simulator"] = "ncsim"
            tester.compile_and_run(**kwargs)
        mock_debugger(run_test)
