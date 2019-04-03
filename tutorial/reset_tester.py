import fault


class ResetTester(fault.Tester):
    def __init__(self, circuit, clock, reset_port):
        super().__init__(circuit, clock)
        self.reset_port = reset_port

    def reset(self):
        self.poke(self.reset_port, 1)
        self.eval()
        self.poke(self.reset_port, 0)
        self.eval()
