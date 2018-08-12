import fault
from fault.common import get_renamed_port
from fault import AnyValue


class FunctionalTester(fault.Tester):
    def __init__(self, circuit, clock, functional_model, input_mapping=None):
        super().__init__(circuit, clock)
        self.functional_model = functional_model
        self.input_mapping = input_mapping

    def expect(self, port, value):
        raise RuntimeError("Cannot call expect on FunctionTester, expectations"
                           " are automatically generated based on the"
                           " functional model")

    def eval(self):
        super().eval()
        for name, port in self.circuit.interface.ports.items():
            if port.isinput():
                fn_model_port = get_renamed_port(self.circuit, name)
                super().expect(port, getattr(self.functional_model,
                                             fn_model_port))

    def expect_any_outputs(self):
        for name, port in self.circuit.interface.ports.items():
            if port.isinput():
                fn_model_port = get_renamed_port(self.circuit, name)
                setattr(self.functional_model, fn_model_port, AnyValue)
