class Tuple:
    def __init__(self, keys, values):
        self.keys = keys
        self.values = values

    def __getitem__(self, index):
        return self.values[self.keys.index(index)]

    def __setitem__(self, index, value):
        self.values[self.keys.index(index)] = value

    def __eq__(self, other):
        if not isinstance(other, Tuple):
            return False
        return self.keys == other.keys and self.values == other.values

    def __len__(self):
        return len(self.keys)

    # @property
    # def flattened_length(self):
    #     if isinstance(self.value, Array):
    #         return self.N * self.value.flattened_length
    #     else:
    #         return self.N

    # def flattened(self):
    #     if isinstance(self.value, Array):
    #         return self.value.flattened()
    #     else:
    #         return self.value

    def __str__(self):
        return f"Tuple({self.keys}, {self.values})"

    def __repr__(self):
        return f"Tuple({self.keys}, {self.values})"
