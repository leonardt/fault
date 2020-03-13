import magma as m
from fault.codegen import CodeGenerator
from fault import ElectIn, ElectOut, RealIn, RealOut


class VAMSPort():
    def __init__(self, dir_, type_, name):
        self.dir_ = dir_
        self.type_ = type_
        self.name = name

    def __str__(self):
        return f'{self.dir_} {self.type_} {self.name}'


class VerilogAMSCode(CodeGenerator):
    def include(self, file):
        self.println(f'`include "{file}"')

    def start_module(self, name, *ports):
        self.println(f'module {name} (')
        self.println_comma_sep(*[f'{port}' for port in ports])
        self.println(');')
        self.indent()

    def instantiate(self, mod_name, *wiring, inst_name=None):
        # set defaults
        if inst_name is None:
            inst_name = f'tmp{next(self.inst_count)}'

        self.println(f'{mod_name} {inst_name} (')
        self.println_comma_sep(*[
            f'.{a}({b})' for a, b in wiring
        ])
        self.println(');')

    def end_module(self):
        self.dedent()
        self.println('endmodule')


def VAMSWrap(circ, wrap_name=None, inst_name=None, tab='    ', nl='\n'):
    # Set defaults
    wrap_name = (wrap_name if wrap_name is not None
                 else f'{circ.name}_wrap')
    inst_name = (inst_name if inst_name is not None
                 else f'{circ.name}_inst')

    # instantiate code generator
    gen = VerilogAMSCode(tab=tab, nl=nl)

    # include files
    gen.include('disciplines.vams')
    gen.emptyln()

    # module definition
    ports = []
    for name, type_ in circ.IO.ports.items():
        # determine port direction
        if type_.is_input():
            vams_dir = 'input'
        elif type_.is_output():
            vams_dir = 'output'
        elif type_.is_inout():
            vams_dir = 'input'
        else:
            raise Exception(f'Unsupported port type: {type_}')

        # determine port type
        if type_ is ElectIn or type_ is ElectOut:
            vams_type = 'electrical'
        elif type_ is RealIn or type_ is RealOut:
            vams_type = 'wreal'
        elif len(type_) == 1:
            vams_type = 'wire'
        else:
            vams_type = f'wire [{len(type_) - 1}:0]'

        # add port to list of ports
        ports += [VAMSPort(dir_=vams_dir, type_=vams_type, name=f'{name}')]
    gen.start_module(wrap_name, *ports)
    gen.emptyln()

    # Generate wiring withing the module instantiation
    wiring = []
    for name in circ.IO.ports.keys():
        wiring += [(f'{name}', f'{name}')]
    gen.instantiate(f'{circ.name}', *wiring, inst_name=inst_name)
    gen.emptyln()

    # end the module
    gen.end_module()

    # Create magma circuit for wrapper
    io_kwargs = {}
    for name, type_ in circ.IO.ports.items():
        io_kwargs[f'{name}'] = type_

    # declare circuit that will be returned
    class wrap_cls(m.Circuit):
        name = f'{wrap_name}'
        io = m.IO(**io_kwargs)

    # Poke the VerilogAMS code into the magma circuit (a bit hacky...)
    wrap_cls.vams_code = gen.text
    wrap_cls.vams_inst_name = inst_name

    # Return the magma circuit
    return wrap_cls
