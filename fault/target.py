from abc import ABC, abstractmethod


class Target(ABC):
    def __init__(self, circuit, actions):
        self.circuit = circuit
        self.actions = actions

    @abstractmethod
    def run(self):
        pass
