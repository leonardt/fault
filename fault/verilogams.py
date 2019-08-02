import magma as m

src_tpl = '''\
`include "disciplines.vams"

module {wrapper_name} ({port_io}
);

{port_types}

    {mod_name} {inst_name} ({inst_wiring}
    );

endmodule'''


class VAMSPort:
    def __init__(self, name, type_, dir_):
        # input validation to catch typos
        assert dir_.lower() in ['input', 'output']

        # save settings
        self.name = name
        self.type_ = type_
        self.dir_ = dir_

    def io_entry(self):
        return f'{self.dir_} {self.name}'

    def type_entry(self):
        return f'{self.type_} {self.name};'

    def is_analog(self):
        return self.type_.lower() == 'analog'

    def is_digital(self):
        return self.type_.lower() == 'digital'

    def magma_io(self):
        if self.dir_.lower() == 'input':
            return m.In(self.magma_type())
        elif self.dir_.lower() == 'output':
            return m.Out(self.magma_type())
        else:
            raise Exception(f'Unsupported I/O direction: {self.dir_}')

    def magma_type(self):
        raise NotImplementedError


class AnalogVAMSPort(VAMSPort):
    def __init__(self, name, dir_):
        super().__init__(name=name, type_='electrical', dir_=dir_)

    def magma_type(self):
        return m.Bit


class DigitalVAMSPort(VAMSPort):
    def __init__(self, name, dir_, width=1, bus=None):
        # the user doesn't have to set the 'bus' argument unless they
        # really want a 1-bit bus.  this flexibility seems to be
        # useful, however because some simulators exhibit minor differences
        # between a single bit ('wire a') and a 1-bit bus ('wire [0:0] a'])
        if bus is None:
            bus = width > 1
        elif width > 1:
            assert bus, 'Multi-bit signals must be declared as a bus.'

        # save settings
        self.width = width
        self.bus = bus

        # determine the string representation of the wire type
        type_ = 'wire'
        if bus:
            type_ += f' [{width-1}:0]'

        # call the super constructor
        super().__init__(name=name, type_=type_, dir_=dir_)

    def magma_type(self):
        if self.bus:
            return m.Bits[self.width]
        else:
            return m.Bit


class VerilogAMSWrapper:
    def __init__(self, mod_name, ports=None, wrapper_name=None, inst_name=None):
        self.mod_name = mod_name
        self.ports = ports if ports is not None else []
        self.wrapper_name = (wrapper_name if wrapper_name is not None
                             else f'{self.mod_name}_wrapper')
        self.inst_name = (inst_name if inst_name is not None
                          else f'{self.mod_name}_inst')

    def generate_code(self, tab='    ', nl='\n'):
        port_io = [nl + tab + port.io_entry() for port in self.ports]
        port_io = ','.join(port_io)

        port_types = [tab + port.type_entry() for port in self.ports]
        port_types = '\n'.join(port_types)

        inst_wiring = [f'{nl}{2*tab}.{port.name}({port.name})'
                       for port in self.ports]
        inst_wiring = ','.join(inst_wiring)

        src = src_tpl.format(
            wrapper_name=self.wrapper_name,
            port_io=port_io,
            port_types=port_types,
            mod_name=self.mod_name,
            inst_name=self.inst_name,
            inst_wiring=inst_wiring
        )

        return src

    def declare_circuit(self):
        args = []
        for port in self.ports:
            args += [port.name, port.magma_io()]

        print(args)

        return m.DeclareCircuit(f'{self.wrapper_name}', *args)
