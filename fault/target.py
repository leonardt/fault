from abc import ABC, abstractmethod


class Target(ABC):
    def __init__(self, circuit):
        self.circuit = circuit

    @abstractmethod
    def run(self):
        pass
