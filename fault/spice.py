from fault.codegen import CodeGenerator


class SpiceNetlist(CodeGenerator):
    def comment(self, text=None):
        # generate comment string
        if text is None:
            c = ''
        else:
            c = f' {text}'
        # print the comment
        self.println(f'*{c}')

    def ic(self, cond):
        line = []
        line += ['.ic']
        for key, val in cond.items():
            line += [f'v({key})={val}']
        self.println(' '.join(line))

    def probe(self, *probes, wrap=False, antype=None):
        line = []
        line += ['.probe']
        if antype is not None:
            line += [f'{antype}']
        for p in probes:
            if wrap:
                line += [f'V({p})']
            else:
                line += [f'{p}']
        self.println(' '.join(line))

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

    @staticmethod
    def ordered_ports(mapping=None, order=None):
        # set defaults
        if mapping is None:
            mapping = {}
        if order is None:
            order = []

        # return ordered list of ports
        retval = []
        for port in order:
            retval += [mapping[port]]
        return retval

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

    def capacitor(self, p, n, value, inst_name=None):
        # set defaults
        if inst_name is None:
            inst_name = f'{next(self.inst_count)}'

        # build up the line
        line = []
        line += [f'C{inst_name}']
        line += [f'{p}', f'{n}']
        line += [f'{value}']

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

    def tran(self, t_step, t_stop, uic=False):
        line = []
        line += ['.tran']
        line += [f'{t_step}']
        line += [f'{t_stop}']
        if uic:
            line += ['uic']
        self.println(' '.join(line))

    def start_subckt(self, name, *ports):
        port_str = ' '.join(ports)
        self.println(f'.subckt {name} {port_str}')
        self.indent()

    def start_control(self):
        self.println('.control')

    def end_control(self):
        self.println('.endc')

    def end_subckt(self):
        self.dedent()
        self.println('.ends')

    def end_file(self):
        self.println('.end')
