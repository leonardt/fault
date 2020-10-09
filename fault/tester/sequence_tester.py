from .staged_tester import Tester


class Sequence:
    def __init__(self, values: list):
        self._values = values

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)


class InputSequence(Sequence):
    pass


class OutputSequence(Sequence):
    pass


class SequenceTester(Tester):
    def __init__(self, circuit, sequences, clock=None):
        """
        sequences: Sequence of pairs (driver/monitor, sequence)

        sequences will be partitioned into input/output sequences

        flow of execution:
        * run input drivers for next value in each input sequence
        * eval (no clock) or step(2) (clock)
        * run output monitors for next value in each output sequence

        will run `n` interations where `n` is the shortest lengths sequence in
        `sequences`
        """
        super().__init__(circuit, clock)
        inputs = []
        outputs = []
        length = None
        for seq in sequences:
            if length is None:
                length = len(seq[1])
            else:
                length = min(length, len(seq[1]))
            if isinstance(seq[1], InputSequence):
                inputs.append((seq[0], iter(seq[1])))
            else:
                assert isinstance(seq[1], OutputSequence)
                outputs.append((seq[0], iter(seq[1])))


        for _ in range(length):
            for driver, sequence in inputs:
                driver(self, next(sequence))

            if clock is None:
                self.eval()
            else:
                self.step(2)

            for monitor, sequence in outputs:
                monitor(self, next(sequence))
