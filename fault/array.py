class Array:
    def __init__(self, value, N):
        self.value = value
        self.N = N

    def __getitem__(self, index):
        return self.value[index]

    def __setitem__(self, index, value):
        self.value[index] = value

    def __eq__(self, other):
        if not isinstance(other, Array):
            return False
        return self.N == other.N and self.value == other.value

    def __len__(self):
        return self.N

    @property
    def flattened_length(self):
        if isinstance(self.value, Array):
            return self.N * self.value.flattened_length
        else:
            return self.N

    def flattened(self):
        if isinstance(self.value, Array):
            return self.value.flattened()
        else:
            return self.value
