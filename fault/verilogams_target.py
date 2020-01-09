from pathlib import Path
from .select_path import SelectPath
from .system_verilog_target import SystemVerilogTarget

try:
    from decida.SimulatorNetlist import SimulatorNetlist
except ModuleNotFoundError:
    print('Failed to import DeCiDa for VerilogAMSTarget.')


class VerilogAMSTarget(SystemVerilogTarget):
    def __init__(self, circuit, simulator='ncsim', directory='build/',
                 model_paths=None, stop_time=1, vsup=1.0, rout=1, flags=None,
                 ext_srcs=None, use_spice=None, use_input_wires=True,
                 ext_model_file=True, bus_delim='<>', ic=None, **kwargs):
        """
        simulator: Name of the simulator to be used for simulation.
        model_paths: paths to SPICE/Spectre files used in the simulation
        stop_time: simulation time passed to the analog solver.  must be
        longer than the mixed-signal simulation duration, or simulation will
        end before encountering $finish.
        vsup: supply voltage assumed for D/A and A/D conversions
        rout: output resistance assumed for D/A conversions
        flags: Additional flags to be passed to the simulator.  Certain
        additional flags will be tacked onto this before passing to the
        SystemVerilogTarget.
        ext_srcs: Additional source files to be compiled when building this
        simulation.
        use_spice: List of names of modules that should use a spice model
        rather than a verilog model.  Not always required, but sometimes
        needed when instantiating a spice module directly in SystemVerilog
        code.
        use_input_wires: If True, drive DUT inputs through wires that are
        in turn assigned to a reg.  This helps with proper discipline
        resolution for Verilog-AMS simulation.
        ext_model_file: If True, don't include the assumed model name in the
        list of Verilog sources.  The assumption is that the user has already
        taken care of this via ext_srcs.
        bus_delim: '<>', '[]', or '_' indicating bus styles "a<3>", "b[2]",
        c_1.
        ic: Dictionary mapping nets or SelectPaths to initialization values.
        """

        # save settings
        self.stop_time = stop_time
        self.vsup = vsup
        self.rout = rout
        self.bus_delim = bus_delim
        self.ic = ic if ic is not None else {}

        # save file names that will be written
        self.amscf = 'amscf.scs'
        self.vamsf = f'{circuit.name}.vams'

        # update simulator argument
        assert simulator == 'ncsim', 'Only the ncsim simulator is allowed at this time.'  # noqa

        # update flags argument
        flags = flags if flags is not None else []

        # update use_spice
        if model_paths is None:
            model_paths = []
        if use_spice is None:
            subckts = set()
            for model_path in model_paths:
                parser = SimulatorNetlist(f'{model_path}')
                subckts.update(parser.get('subckts'))
            use_spice = list(subckts)
        self.use_spice = use_spice

        # update model paths
        for path in model_paths:
            path = Path(path).resolve()
            flags += ['-modelpath', f'{path}']

        # update ext_srcs
        ext_srcs = ext_srcs if ext_srcs is not None else []
        ext_srcs += [self.amscf]
        if hasattr(circuit, 'vams_code'):
            ext_srcs += [self.vamsf]

        # call the superconstructor
        super().__init__(circuit=circuit, simulator=simulator, flags=flags,
                         ext_srcs=ext_srcs, directory=directory,
                         use_input_wires=use_input_wires,
                         ext_model_file=ext_model_file, **kwargs)

    def run(self, *args, **kwargs):
        # write the AMS control file
        self.write_amscf()

        # write the VAMS wrapper (if needed)
        if hasattr(self.circuit, 'vams_code'):
            self.write_vamsf()

        # then call the super constructor
        super().run(*args, **kwargs)

    def gen_amscf(self, tab='    ', nl='\n'):
        # specify which modules instantiated in SystemVerilog code
        # should use SPICE models
        amsd_lines = ''
        for model in self.use_spice:
            amsd_lines += f'{tab}config cell={model} use=spice{nl}'
            amsd_lines += f'{tab}portmap subckt={model} autobus=yes busdelim="{self.bus_delim}"{nl}'  # noqa

        # build up the output lines
        lines = []
        lines += [f'tranSweep tran stop={self.stop_time}s']
        if self.ic:
            # generate path to instantiated spice circuit
            path_to_spice = []
            path_to_spice += [f'{self.circuit.name}_tb']
            path_to_spice += ['dut']
            path_to_spice += [self.circuit.vams_inst_name]
            path_to_spice = '.'.join(path_to_spice)

            # generate all key assignments
            ic_line = []
            ic_line += ['ic']
            for key, val in self.ic.items():
                if isinstance(key, SelectPath):
                    name = f'{path_to_spice}.{key.spice_path}'
                else:
                    name = f'{path_to_spice}.{key}'
                ic_line += [f'{name}={val}']
            lines += [' '.join(ic_line)]
        lines += [f'''\
amsd {{
    ie vsup={self.vsup} rout={self.rout}
{amsd_lines}
}}''']

        # return amscf text
        return nl.join(lines)

    def write_amscf(self):
        with open(self.directory / Path(self.amscf), 'w') as f:
            f.write(self.gen_amscf())

    def write_vamsf(self):
        with open(self.directory / Path(self.vamsf), 'w') as f:
            f.write(self.circuit.vams_code)
