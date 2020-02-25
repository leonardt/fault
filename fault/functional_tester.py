import fault
from fault.common import get_renamed_port
from fault import AnyValue


class FunctionalTester(fault.Tester):
    """
    This Tester provides a convenience mechanism for verifying a DUT against a
    functional model.  The basic pattern is that every time `eval` is invoked
    on the Tester, a check is done to verify that the current outputs of the
    functional model are equivalent to the outputs of the DUT.  This pattern
    works best with a model that is fairly low-level (e.g. cycle accurate). The
    user has the flexibility to relax accuracy of the model by setting the
    outputs of the functional model to be `fault.AnyValue`.  Anything is equal
    to `fault.AnyValue`, so the user can manage when to actually perform the
    consistency check by only updating `fault.AnyValue` at the appropriate
    time.
    """
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
        for name, port in self._circuit.interface.ports.items():
            if port.is_input():
                fn_model_port = get_renamed_port(self._circuit, name)
                super().expect(port, getattr(self.functional_model,
                                             fn_model_port))

    def expect_any_outputs(self):
        for name, port in self._circuit.interface.ports.items():
            if port.is_input():
                fn_model_port = get_renamed_port(self._circuit, name)
                setattr(self.functional_model, fn_model_port, AnyValue)
