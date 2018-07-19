from abc import ABC, abstractmethod


class Target(ABC):
    def __init__(self, circuit, test_vectors):
        self._circuit = circuit
        self._test_vectors = test_vectors

    @abstractmethod
    def run(self):
        pass
