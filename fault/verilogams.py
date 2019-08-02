import magma as m
from magma.bit import BitKind, BitType
from magma.port import INPUT, OUTPUT

class AnalogKind(BitKind):
    pass

class AnalogType(BitType):
    pass

def MakeAnalog(**kwargs):
    return AnalogKind('Analog', (AnalogType,), kwargs)

Analog = MakeAnalog()
AnalogIn = MakeAnalog(direction=INPUT)
AnalogOut = MakeAnalog(direction=OUTPUT)

src_tpl = '''\
`include "disciplines.vams"

module {wrap_name} ({port_io}
);

{port_types}

    {circ_name} {inst_name} ({inst_wiring}
    );

endmodule'''

class VerilogAMSWrapper:
    def __init__(self, circuit, wrap_name=None, inst_name=None):
        self.circuit = circuit
        self.wrap_name = (wrap_name if wrap_name is not None
                             else f'{self.circ_name}_wrap')
        self.inst_name = (inst_name if inst_name is not None
                          else f'{self.circ_name}_inst')

    @property
    def circ_name(self):
        return self.circuit.name

    @staticmethod
    def io_entry(name, type_):
        retval = ''

        if type_.isinput():
            retval += 'input'
        elif type_.isoutput():
            retval += 'output'
        else:
            raise Exception(f'Only inputs and outputs are supported.')

        retval += f' {name}'

        return retval

    @staticmethod
    def type_entry(name, type_):
        if isinstance(type_, AnalogKind):
            return f'electrical {name};'
        else:
            return f'wire [{type_.size()-1}:0] {name};'

    def generate_code(self, tab='    ', nl='\n'):
        port_io = [nl + tab + self.io_entry(name=name, type_=type_) 
                   for name, type_ in self.circuit.IO.ports.items()]
        port_io = ','.join(port_io)

        port_types = [tab + self.type_entry(name=name, type_=type_)
                      for name, type_ in self.circuit.IO.ports.items()]
        port_types = '\n'.join(port_types)

        inst_wiring = [f'{nl}{2*tab}.{name}({name})'
                       for name in self.circuit.IO.ports.keys()]
        inst_wiring = ','.join(inst_wiring)

        src = src_tpl.format(
            wrap_name=self.wrap_name,
            port_io=port_io,
            port_types=port_types,
            circ_name=self.circ_name,
            inst_name=self.inst_name,
            inst_wiring=inst_wiring
        )

        return src

    def declare_circuit(self):
        args = []
        for port in self.ports:
            args += [port.name, port.magma_io()]

        return m.DeclareCircuit(f'{self.wrap_name}', *args)
