from itertools import count

class SpiceNetlist:
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

    def comment(self, text):
        self.println(f'* {text}')

    def include(self, file_):
        self.println(f'.include {file_}')

    def options(self, *args):
        # build up the line
        line = []
        line += ['.options']
        line += [f'{arg}' for arg in args]

        # print the line
        self.println(' '.join(line))

    def model(self, mod_name, mod_type, **kwargs):
        line = []
        line += ['.model']
        line += [f'{mod_name}']
        line += [f'{mod_type}']
        for key, val in kwargs.items():
            line += [f'{key}={val}']
        line = ' '.join(line)
        self.println(line)

    def instantiate(self, name, *ports, inst_name=None):
        # set defaults
        if inst_name is None:
            inst_name = f'{next(self.inst_count)}'

        # print the instantiation string
        port_str = ' '.join(f'{port}' for port in ports)
        self.println(f'X{inst_name} {port_str} {name}')

    def voltage(self, p, n, dc=None, pwl=None, inst_name=None):
        # set defaults
        if inst_name is None:
            inst_name = f'{next(self.inst_count)}'
        if dc is None and pwl is not None:
            dc = pwl[0][1]

        # build up the line
        line = []
        line += [f'V{inst_name}']
        line += [f'{p}', f'{n}']
        if dc is not None:
            line += ['DC', f'{dc}']
        if pwl is not None:
            pwl_str = ' '.join(f'{t} {v}' for t, v in pwl)
            line += [f'PWL({pwl_str})']

        # print the line
        self.println(' '.join(line))

    def switch(self, sw_p, sw_n, ctl_p, ctl_n, mod_name, inst_name=None,
               default=None):
        # set defaults
        if inst_name is None:
            inst_name = f'{next(self.inst_count)}'

        # build up the line
        line = []
        line += [f'S{inst_name}']
        line += [f'{sw_p}', f'{sw_n}', f'{ctl_p}', f'{ctl_n}']
        line += [f'{mod_name}']
        if default is not None:
            line += [f'{default}']

        # print the line
        self.println(' '.join(line))

    def vcr(self, p, n, ctl_p, ctl_n, pwl, inst_name=None):
        # set defaults
        if inst_name is None:
            inst_name = f'{next(self.inst_count)}'

        # build up the line
        line = []
        line += [f'G{inst_name}']
        line += [f'{p}', f'{n}']
        line += ['VCR', 'PWL(1)']
        line += [f'{ctl_p}', f'{ctl_n}']
        for v, r in pwl:
            line += [f'{v}v,{r}']

        # print the line
        self.println(' '.join(line))

    def tran(self, t_step, t_stop):
        self.println(f'.tran {t_step} {t_stop}')

    def start_subckt(self, name, *ports):
        port_str = ' '.join(ports)
        self.println(f'.subckt {name} {port_str}')
        self.indent()

    def end_subckt(self):
        self.dedent()
        self.println('.ends')

    def end_file(self):
        self.println('.end')

    def print(self, *args):
        for arg in args:
            self.text += arg

    def println(self, *args):
        for arg in args:
            self.text += f'{self.tab_count*self.tab}{arg}{self.nl}'

    def write_to_file(self, fname):
        with open(fname, 'w') as f:
            f.write(self.text)