from bit_vector import BitVector
import magma
import fault.actions as actions
from fault.value_utils import make_value
from fault.value import AnyValue


class VectorBuilder:
    def __init__(self, circuit):
        self.circuit = circuit
        self.port_to_index = {}
        for i, port in enumerate(self.circuit.interface.ports.values()):
            self.port_to_index[port] = i
        self.vectors = [self.__empty_vector()]

    def __empty_vector(self):
        ports = self.circuit.interface.ports
        return [make_value(port, AnyValue) for port in ports.values()]

    def __indices(self, port):
        if port in self.port_to_index:
            return (self.port_to_index[port],)
        if isinstance(port.name, magma.ref.ArrayRef):
            indices = self.__indices(port.name.array)
            return (*indices, port.name.index)
        raise NotImplementedError(port, type(port))

    def __get(self, indices):
        out = self.vectors[-1]
        for idx in indices:
            out = out[idx]
        return out

    def __set(self, indices, value):
        parent = self.vectors[-1]
        for idx in indices[:-1]:
            parent = parent[idx]
        parent[indices[-1]] = value

    def __eval(self):
        self.vectors.append(self.vectors[-1].copy())
        for port in self.circuit.interface.ports.values():
            if port.isinput():
                index = self.port_to_index[port]
                self.vectors[-1][index] = make_value(port, AnyValue)

    def process(self, action):
        if isinstance(action, (actions.Poke, actions.Expect)):
            indices = self.__indices(action.port)
            self.__set(indices, action.value)
        elif isinstance(action, actions.Eval):
            self.__eval()
        elif isinstance(action, actions.Step):
            indices = self.__indices(action.clock)
            val = self.__get(indices)
            for step in range(action.steps):
                val ^= BitVector(1, 1)
                self.__eval()
                self.__set(indices, val)
        elif isinstance(action, actions.Print):
            # Skip Print actions for test vectors
            return
        else:
            raise NotImplementedError(action)
