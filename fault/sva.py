class SVAProperty:
    def __init__(self, args):
        self.args = args


def sva(*args):
    return SVAProperty(args)
