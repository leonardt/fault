import magma as m
from magma.bit import BitKind, BitType
from magma.port import INPUT, OUTPUT

# Very preliminary implementation of analog types
# This should probably be moved to magma at some point

class AnalogKind(BitKind):
    pass

class AnalogType(BitType):
    pass

def MakeAnalog(**kwargs):
    return AnalogKind('Analog', (AnalogType,), kwargs)

Analog = MakeAnalog()
AnalogIn = MakeAnalog(direction=INPUT)
AnalogOut = MakeAnalog(direction=OUTPUT)

# Class that can wrap an existing magma circuit in a Verilog-AMS shell
# In the future, various special measurement and stimulus features
# might be added here.

class VerilogAMSWrapper:
    def __init__(self, circuit, wrap_name=None, inst_name=None):
        self.circuit = circuit
        self.wrap_name = (wrap_name if wrap_name is not None
                             else f'{self.circ_name}_wrap')
        self.inst_name = (inst_name if inst_name is not None
                          else f'{self.circ_name}_inst')

    @property
    def circ_name(self):
        # returns the name of the circuit being wrapped

        return self.circuit.name

    @staticmethod
    def io_entry(name, type_):
        # returns the port list declaration for the given port

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
        # return the type declaration string
        # for the given port

        if isinstance(type_, AnalogKind):
            return f'electrical {name};'
        else:
            return f'wire [{type_.size()-1}:0] {name};'

    def generate_code(self, tab='    ', nl='\n'):
        # Returns a string containing the VerilogAMS implementation 
        # of the wrapper.

        # generate port list declarations
        port_io = [nl + tab + self.io_entry(name=name, type_=type_) 
                   for name, type_ in self.circuit.IO.ports.items()]
        port_io = ','.join(port_io)

        # generate type declarations
        port_types = [tab + self.type_entry(name=name, type_=type_)
                      for name, type_ in self.circuit.IO.ports.items()]
        port_types = '\n'.join(port_types)

        # generate wiring withing the module instantiation
        inst_wiring = [f'{nl}{2*tab}.{name}({name})'
                       for name in self.circuit.IO.ports.keys()]
        inst_wiring = ','.join(inst_wiring)

        # render the text template
        src = self.src_tpl.format(
            wrap_name=self.wrap_name,
            port_io=port_io,
            port_types=port_types,
            circ_name=self.circ_name,
            inst_name=self.inst_name,
            inst_wiring=inst_wiring
        )

        return src

    def make_wrap_circ(self):
        # Returns a magma circuit representing the wrapped circuit.

        args = []
        for name, type_ in self.circuit.IO.ports.items():
            args += [name, type_]

        return m.DeclareCircuit(f'{self.wrap_name}', *args)
    
    # Template used for generating the VerilogAMS implementation
    src_tpl = '''\
`include "disciplines.vams"

module {wrap_name} ({port_io}
);

{port_types}

    {circ_name} {inst_name} ({inst_wiring}
    );

endmodule'''
