class SVAProperty:
    def __init__(self, args):
        self.args = args


def sva(*args):
    new_args = tuple()
    # Escape format chars
    for arg in args:
        if isinstance(arg, str):
            arg = arg.replace("{", "{{").replace("}", "}}")
        new_args += (arg,)
    return SVAProperty(new_args)
