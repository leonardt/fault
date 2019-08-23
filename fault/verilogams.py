import magma as m
from fault.codegen import CodeGenerator
from fault import ElectIn, ElectOut, RealIn, RealOut


class VerilogAMSCode(CodeGenerator):
    def include(self, file):
        self.println(f'`include "{file}"')

    def start_module(self, name, *ports):
        self.println(f'module {name} (')
        self.println_comma_sep(*[
            f'{io_dir} {io_name}' for io_dir, io_name in ports
        ])
        self.println(');')
        self.indent()

    def decl_port_type(self, type_, name):
        self.println(f'{type_} {name};')

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
        if type_.isinput():
            ports += [('input', f'{name}')]
        elif type_.isoutput():
            ports += [('output', f'{name}')]
        elif type_.isinout():
            ports += [('inout', f'{name}')]
        else:
            raise Exception(f'Unsupported port type: {type_}')
    gen.start_module(wrap_name, *ports)
    gen.emptyln()

    # declare port types
    for name, type_ in circ.IO.ports.items():
        if type_ is ElectIn or type_ is ElectOut:
            vams_type = 'electrical'
        elif type_ is RealIn or type_ is RealOut:
            vams_type = 'wreal'
        else:
            vams_type = f'wire [{type_.size() - 1}:0]'
        gen.decl_port_type(vams_type, f'{name}')
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
    magma_args = []
    for name, type_ in circ.IO.ports.items():
        magma_args += [name, type_]
    retval = m.DeclareCircuit(f'{wrap_name}', *magma_args)

    # Poke the VerilogAMS code into the magma circuit
    # (a bit hacky, probably should use a subclass instead)
    retval.vams_code = gen.text
    retval.vams_inst_name = inst_name

    # Return the magma circuit
    return retval
