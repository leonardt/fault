import magma as m
from fault.verilog_target import VerilogTarget, verilog_name
from pathlib import Path
import fault.utils as utils
import os
import ast
import astor


class BVReplacer(ast.NodeTransformer):
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "BitVector":
            assert isinstance(node.args[0], ast.Num), \
                "Non constant BVs not implemented"
            assert isinstance(node.args[1], ast.Num), \
                "Non constant BVs not implemented"
            return ast.Name(str(node.args[0].n) + "_" + str(node.args[1].n),
                            ast.Load())
        return node


class SelfPrefixer(ast.NodeTransformer):
    def __init__(self, name):
        self.name = name

    def visit_Name(self, node):
        if node.id == self.name:
            return ast.Attribute(ast.Name("self", ast.Load()),
                                 node.id, node.ctx)
        return node


def get_width(port):
    if isinstance(port, m._BitType):
        return 1
    return len(port)


class CoSATarget(VerilogTarget):
    def __init__(self, circuit, directory="build/", skip_compile=False,
                 include_verilog_libraries=[], magma_output="coreir-verilog",
                 circuit_name=None, magma_opts={}, solver="msat"):
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         include_verilog_libraries, magma_output, magma_opts)
        self.state_index = 0
        self.curr_state_pokes = []
        self.step_offset = 0
        self.states = []
        self.solver = solver

    def make_eval(self, i, action):
        raise NotImplementedError()

    def make_expect(self, i, action):
        raise NotImplementedError()

    def make_poke(self, i, action):
        name = verilog_name(action.port.name)
        value = action.value
        width = get_width(action.port)
        # self.curr_state_pokes.append(
        #     f"{name} = {value}_{width}")
        self.curr_state_pokes.append(
            f"self.{name} = {value}_{width}")

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

    def make_step(self, i, action):
        self.step_offset += action.steps
        if self.step_offset % 2 == 0:
            if len(self.states) > 0:
                prefix = f"S{len(self.states) - 1}"
            else:
                prefix = "I"
            self.states.append("\n".join(
                f"{prefix}: {poke}" for poke in
                self.curr_state_pokes))
            self.states[-1] += f"\n{prefix}: pokes_done = False\n"
            self.curr_state_pokes = []

    def add_assumptions(self):
        assumptions = []
        for assumption in self.assumptions:
            code = utils.get_short_lambda_body_text(assumption.value)
            tree = ast.parse(code)
            tree = self.prefix_io_with_self(tree)
            tree = self.replace_bvs(tree)

            code = astor.to_source(tree).rstrip()
            assumptions.append(code)
        assumptions = ";".join(x for x in assumptions)
        return assumptions

    def prefix_io_with_self(self, tree):
        for name in self.circuit.interface.ports.keys():
            tree = SelfPrefixer(name).visit(tree)
        return tree

    def replace_bvs(self, tree):
        tree = BVReplacer().visit(tree)
        return tree

    def generate_code(self, actions):
        for i, action in enumerate(actions):
            code = self.generate_action_code(i, action)
        ets = ""
        # model_files = f"{self.circuit_name}.v[{self.circuit_name}]"
        model_files = f"{self.circuit_name}.json"
        if len(self.states) > 0:
            for state in self.states:
                ets += state + "\n"
            if len(self.states) > 0:
                prefix = f"S{len(self.states) - 2}"
            else:
                prefix = "I"
            ets = "\n".join(ets.splitlines()[:-2])
            ets += f"\n{prefix}: pokes_done = True\n\n"

            ets += f"I -> S{0}\n"
            for i in range(1, len(self.states) - 1):
                ets += f"S{i - 1} -> S{i}\n"
            last_i = len(self.states) - 2
            ets += f"S{last_i} -> S{last_i}\n"
            model_files += f",{self.circuit_name}.ets"
        assumptions = self.add_assumptions()

        src = f"""\
[GENERAL]
model_file: {model_files}
add_clock: True

[DEFAULT]
strategy: ALL
"""
        for i, guarantee in enumerate(self.guarantees):
            formula = utils.get_short_lambda_body_text(guarantee.value)
            tree = ast.parse(formula)
            tree = self.prefix_io_with_self(tree)
            formula = astor.to_source(tree).rstrip()
            # TODO: More robust symbol replacer on AST
            formula = formula.replace("and", "&")
            src += f"""\
[Problem {i}]
assumptions: {assumptions}
formula: pokes_done -> ({formula})
verification: safety
prove: True
expected: True
"""
        return src, ets

    def run(self, actions):
        problem_file = self.directory / Path(f"{self.circuit_name}_problem.txt")
        ets_file = self.directory / Path(f"{self.circuit_name}.ets")
        src, ets = self.generate_code(actions)
        with open(problem_file, "w") as f:
            f.write(src)
        with open(ets_file, "w") as f:
            f.write(ets)
        assert not os.system(
            f"CoSA --problem {problem_file} --solver {self.solver}")
