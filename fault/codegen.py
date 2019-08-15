from itertools import count


class CodeGenerator:
    def __init__(self, tab='    ', nl='\n'):
        # save settings
        self.tab = tab
        self.nl = nl

        # initialize
        self.reset()

    def reset(self):
        self.text = ''
        self.tab_count = 0
        self.inst_count = count()

    def indent(self):
        self.tab_count += 1

    def dedent(self):
        self.tab_count -= 1
        assert self.tab_count >= 0, 'Cannot have a negative number of tabs.'

    def print(self, *args):
        for arg in args:
            self.text += arg

    def emptyln(self):
        self.print(f'{self.nl}')

    def println(self, *args):
        for arg in args:
            self.print(f'{self.tab_count*self.tab}{arg}{self.nl}')

    def println_comma_sep(self, *args, indent=True):
        if indent:
            self.indent()
        for k, arg in enumerate(args):
            line = f'{arg}'
            if k != len(args) - 1:
                line += ','
            self.println(line)
        if indent:
            self.dedent()

    def write_to_file(self, fname):
        with open(fname, 'w') as f:
            f.write(self.text)
