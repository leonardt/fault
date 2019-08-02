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


def vams_io_entry(name, type_):
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


def vams_type_entry(name, type_):
    # return the type declaration string for the given port

    if isinstance(type_, AnalogKind):
        return f'electrical {name};'
    else:
        return f'wire [{type_.size()-1}:0] {name};'


def wrap_circ(circ, wrap_name):
    # Returns a magma circuit representing the wrapped circuit.

    args = []
    for name, type_ in circ.IO.ports.items():
        args += [name, type_]

    return m.DeclareCircuit(f'{wrap_name}', *args)


# Template used for generating the VerilogAMS implementation
src_tpl = '''\
`include "disciplines.vams"

module {wrap_name} ({port_io}
);

{port_types}

    {circ_name} {inst_name} ({inst_wiring}
    );

endmodule'''


def vams_wrap(circ, wrap_name=None, inst_name=None, tab='    ', nl='\n'):
    # Set defaults
    wrap_name = (wrap_name if wrap_name is not None
                 else f'{circ.name}_wrap')
    inst_name = (inst_name if inst_name is not None
                 else f'{circ.name}_inst')

    # Generate port list declarations
    port_io = [nl + tab + vams_io_entry(name=name, type_=type_)
               for name, type_ in circ.IO.ports.items()]
    port_io = ','.join(port_io)

    # Generate type declarations
    port_types = [tab + vams_type_entry(name=name, type_=type_)
                  for name, type_ in circ.IO.ports.items()]
    port_types = '\n'.join(port_types)

    # Generate wiring withing the module instantiation
    inst_wiring = [f'{nl}{2*tab}.{name}({name})'
                   for name in circ.IO.ports.keys()]
    inst_wiring = ','.join(inst_wiring)

    # Render the text template
    vams_code = src_tpl.format(
        wrap_name=wrap_name,
        port_io=port_io,
        port_types=port_types,
        circ_name=circ.name,
        inst_name=inst_name,
        inst_wiring=inst_wiring
    )

    # Create magma circuit for wrapper
    retval = wrap_circ(circ=circ, wrap_name=wrap_name)

    # Poke the VerilogAMS code into the magma circuit
    retval.vams_code = vams_code

    # Return the magma circuit
    return retval
