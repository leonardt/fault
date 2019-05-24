class Expression:
    pass


class BinaryOp(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class And(BinaryOp):
    pass


class EQ(BinaryOp):
    pass


class NE(BinaryOp):
    pass
