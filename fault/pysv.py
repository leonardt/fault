from abc import abstractmethod, ABC, ABCMeta


class PysvMonitor(ABC, metaclass=ABCMeta):
    @abstractmethod
    def observe(self, *args, **kwargs):
        pass
