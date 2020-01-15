import fault
from fault.common import get_renamed_port


def generate_actions_from_streams(circuit, functional_model, streams,
                                  num_vectors=10, input_mapping=None):
    tester = fault.Tester(circuit)

    for i in range(num_vectors):
        inputs = []
        for name, stream in streams.items():
            if callable(stream):
                val = stream(name, getattr(circuit, name))
            else:
                val = stream
            inputs.append(val)
            # stream_port = get_renamed_port(circuit, name)
            tester.poke(getattr(circuit, name), inputs[-1])
        tester.eval()
        # Used to handle differences between circuit's interface and
        # functional_model interface. For example, the simple_cb interface
        # is packed for the genesis version
        if input_mapping:
            inputs = input_mapping(*inputs)
        functional_model(*inputs)
        for name, port in circuit.interface.items():
            if port.is_output():
                # Handle renamed output ports
                fn_model_port = get_renamed_port(circuit, name)
                tester.expect(getattr(circuit, name),
                              getattr(functional_model, fn_model_port))
    return tester.actions
