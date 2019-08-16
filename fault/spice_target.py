import os
from pathlib import Path
import fault.actions
import magma as m
from fault.target import Target
from fault.spice import SpiceNetlist
from fault.nutascii_parse import nutascii_parse
from fault.psf_parse import psf_parse
from fault.subprocess_run import subprocess_run
from fault.pwl import pwc_to_pwl


class SpiceTarget(Target):
    def __init__(self, circuit, directory="build/", simulator='ngspice',
                 vsup=1.0, rout=1, model_paths=None, sim_env=None,
                 t_step=None, clock_step_delay=5, t_tr=0.2e-9, vil_rel=0.4,
                 vih_rel=0.6, rz=1e9, conn_order='alpha', bus_delim='<',
                 bus_order='descend', flags=None):
        """
        circuit: a magma circuit

        directory: directory to use for generating collateral, buildling, and
                   running simulator

        simulator: "ngspice" or "spectre" or "hspice"

        stop_time: simulation time passed to the analog solver.  must be
                   longer than the mixed-signal simulation duration, or
                   simulation will end before encountering $finish.

        vsup: supply voltage assumed for D/A and A/D conversions

        rout: output resistance assumed for D/A conversions

        sim_env: Environment variable definitions to use when running the
                 simulator.  If not provided, the value from os.environ will
                 be used.

        clock_step_delay: Set the number of steps to delay for each step of the
                          clock

        t_step: Hint for simulator as to the printing interval.

        t_tr: transition time for poke statements

        vil_rel: Input "0" level, as a fraction of the supply.

        vih_rel: Input "1" level, as a fraction of the supply.

        rz: resistance of voltage stimulus when set to fault.HiZ

        conn_order: If 'alpha', connect pins in alphabetical order.  If
                    'parse', parse through model_paths looking for the
                    subcircuit definition to determine the pin order.

        bus_delim: '<', '[', or '_' indicating bus styles "a<3>", "b[2]",
                   c_1.

        bus_order: 'descend' or 'ascend', indicating whether buses are
                   order from largest to smallest or smallest to largest,
                   respectively.

        flags: List of additional arguments that should be passed to the
               simulator.
        """
        # call the super constructor
        super().__init__(circuit)

        # sanity check
        if simulator not in {'ngspice', 'spectre', 'hspice'}:
            raise ValueError(f'Unsupported simulator {simulator}')

        # make directory if needed
        os.makedirs(directory, exist_ok=True)

        # save settings
        self.directory = directory
        self.simulator = simulator
        self.vsup = vsup
        self.rout = rout
        self.model_paths = model_paths if model_paths is not None else []
        self.sim_env = sim_env
        self.t_step = t_step
        self.clock_step_delay = clock_step_delay
        self.t_tr = t_tr
        self.vil_rel = vil_rel
        self.vih_rel = vih_rel
        self.rz = rz
        self.conn_order = conn_order
        self.bus_delim = bus_delim
        self.bus_order = bus_order
        self.flags = flags if flags is not None else []

    def run(self, actions):
        # compile the actions
        pwls, checks, stop_time = self.compile_actions(actions)

        # write the testbench
        tb_file = self.write_test_bench(pwls=pwls, stop_time=stop_time)

        # generate simulator commands
        if self.simulator == 'ngspice':
            sim_cmds, raw_file = self.ngspice_cmds(tb_file)
        elif self.simulator == 'spectre':
            sim_cmds, raw_file = self.spectre_cmds(tb_file)
        elif self.simulator == 'hspice':
            sim_cmds, raw_file = self.hspice_cmds(tb_file)
        else:
            raise NotImplementedError(self.simulator)

        # run the simulation commands
        for sim_cmd in sim_cmds:
            res = subprocess_run(sim_cmd, cwd=self.directory, env=self.sim_env)
            assert not res.returncode, f'Error running simulator: {self.simulator}'  # noqa

        # process the results
        if self.simulator in {'ngspice', 'spectre'}:
            results = nutascii_parse(raw_file)
        elif self.simulator in {'hspice'}:
            results = psf_parse(raw_file)
        else:
            raise NotImplementedError(self.simulator)

        # process results
        self.check_results(results=results, checks=checks)

    def compile_actions(self, actions):
        # initialize
        t = 0
        pwc_dict = {}
        checks = []

        # loop over actions handling pokes, expects, and delays
        for action in actions:
            if isinstance(action, fault.actions.Poke):
                # add port to stimulus dictionary if needed
                if action.port.name not in pwc_dict:
                    pwc_dict[action.port.name] = ([], [])
                # determine the stimulus value, performing a digital
                # to analog conversion if needed and controlling
                # the output switch as needed
                if action.value is fault.HiZ:
                    stim_v = 0
                    stim_s = 0
                elif isinstance(action.port, m.BitType):
                    stim_v = self.vsup if action.value else 0
                    stim_s = 1
                else:
                    stim_v = action.value
                    stim_s = 1
                # add the value to the list of actions
                pwc_dict[action.port.name][0].append((t, stim_v))
                pwc_dict[action.port.name][1].append((t, stim_s))
                # increment time
                t += self.clock_step_delay * 1e-9
            elif isinstance(action, fault.actions.Expect):
                checks.append((t, action))
            elif isinstance(action, fault.actions.Delay):
                t += action.time
            else:
                raise NotImplementedError(action)

        # refactor stimulus voltages to PWL
        pwls = {}
        for name, pwc in pwc_dict.items():
            pwls[name] = (
                pwc_to_pwl(pwc=pwc[0], t_stop=t, t_tr=self.t_tr),
                pwc_to_pwl(pwc=pwc[1], t_stop=t, t_tr=self.t_tr, init=1)
            )

        # return PWL waveforms, checks to be performed, and stop time
        return pwls, checks, t

    @staticmethod
    def pwl_str(pwl):
        return ' '.join(f'{t} {v}' for t, v in pwl)

    def get_ordered_ports(self):
        if self.conn_order == 'alpha':
            return self.get_alpha_ordered_ports()
        elif self.conn_order == 'parse':
            raise Exception('Spice parsing is not implemented yet.')
        else:
            raise Exception(f'Unknown conn_order: {self.conn_order}.')

    def bit_from_bus(self, port, k):
        if self.bus_delim == '<':
            return f'{port}<{k}>'
        elif self.bus_delim == '[':
            return f'{port}[{k}]'
        elif self.bus_delim == '_':
            return f'{port}_{k}'
        else:
            raise Exception(f'Unknown bus delimeter: {self.bus_delim}')

    def get_alpha_ordered_ports(self):
        # get ports sorted in alphabetical order
        port_names = self.circuit.interface.ports.keys()
        port_names = sorted(port_names, key=lambda p: f'{p}')

        # expand out buses
        retval = []
        for port_name in port_names:
            port = self.circuit.interface.ports[port_name]
            if isinstance(port, (m.BitType, fault.RealType, fault.ElectType)):
                retval += [f'{port}']
            else:
                if self.bus_order == 'ascend':
                    bit_idx = range(len(port))
                elif self.bus_order == 'descend':
                    bit_idx = reversed(range(len(port)))
                else:
                    raise Exception(f'Unsupported bus order: {self.bus_order}')
                for k in bit_idx:
                    retval += [self.bit_from_bus(port, k)]

        # return ordered list of ports
        return retval

    def write_test_bench(self, pwls, stop_time, tb_file=None):
        # create a new netlist
        netlist = SpiceNetlist()
        netlist.comment('Automatically generated file.')

        # add include files
        for file_ in self.model_paths:
            netlist.include(file_)

        # instantiate the DUT
        dut_name = f'{self.circuit.name}'
        netlist.instantiate(dut_name, *self.get_ordered_ports())

        # define the switch model
        inout_sw_mod = 'inout_sw_mod'
        netlist.start_subckt(inout_sw_mod, 'sw_p', 'sw_n', 'ctl_p', 'ctl_n')
        if self.simulator == 'ngspice':
            sw_model = '__inout_sw_mod'
            netlist.model(mod_name=sw_model, mod_type='sw', vt=0.5, vh=0.2,
                          ron=self.rout, roff=self.rz)
            netlist.switch('sw_p', 'sw_n', 'ctl_p', 'ctl_n',
                           mod_name=sw_model, default='ON')
        elif self.simulator in {'spectre', 'hspice'}:
            netlist.vcr('sw_p', 'sw_n', 'ctl_p', 'ctl_n',
                        pwl=[(0, self.rz), (1, self.rout)])
        netlist.end_subckt()

        # write stimuli lines
        for name, (pwl_v, pwl_s) in pwls.items():
            # instantiate switch between voltage source and DUT
            vnet = f'__{name}_v'
            snet = f'__{name}_s'
            netlist.instantiate('inout_sw_mod', vnet, name, snet, '0')

            # instantiate voltage source connected through switch
            netlist.voltage(vnet, '0', pwl=pwl_v)
            netlist.voltage(snet, '0', pwl=pwl_s)

        # specify the transient analysis
        t_step = self.t_step if self.t_step is not None else stop_time / 1000
        netlist.tran(t_step=t_step, t_stop=stop_time)

        # generate control statement
        if self.simulator == 'ngspice':
            netlist.start_control()
            netlist.println('run')
            netlist.println('set filetype=ascii')
            netlist.println('write')
            netlist.println('exit')
            netlist.end_control()
        elif self.simulator == 'hspice':
            netlist.options('post')

        # end the netlist
        netlist.end_file()

        # write spice file
        tb_file = (tb_file if tb_file is not None
                   else Path(self.directory) / f'{self.circuit.name}_tb.sp')
        tb_file = tb_file.absolute()
        netlist.write_to_file(tb_file)

        # return name of the file written
        return tb_file

    def impl_expect(self, results, time, action):
        # get value
        name = f'{action.port.name}'.split('.')[-1]

        # get value, performing analog to digital conversion
        # if necessary
        value = results[name](time)
        if isinstance(action.port, m.BitType):
            if value <= self.vil_rel * self.vsup:
                value = 0
            elif value >= self.vih_rel * self.vsup:
                value = 1
            else:
                raise Exception(f'Invalid logic level: {value}.')

        # implement the requested check
        if action.above is not None:
            if action.below is not None:
                assert action.above <= value <= action.below, f'Expected {action.above} to {action.below}, got {value}'  # noqa
            else:
                assert action.above <= value, f'Expected above {action.above}, got {value}'  # noqa
        else:
            if action.below is not None:
                assert value <= action.below, f'Expected below {action.below}, got {value}'  # noqa
            else:
                assert value == action.value, f'Expected {action.value}, got {value}'  # noqa

    def check_results(self, results, checks):
        for check in checks:
            self.impl_expect(results=results, time=check[0], action=check[1])

    def ngspice_cmds(self, tb_file):
        # build up the command
        cmd = []
        cmd += ['ngspice']
        cmd += ['-b']
        cmd += [f'{tb_file}']
        raw_file = (Path(self.directory) / 'out.raw').absolute()
        cmd += ['-r', f'{raw_file}']
        cmd += self.flags

        # return command and corresponding raw file
        return [cmd], raw_file

    def spectre_cmds(self, tb_file):
        # build up the command
        cmd = []
        cmd += ['spectre']
        cmd += [f'{tb_file}']
        cmd += ['-format', 'nutascii']
        raw_file = (Path(self.directory) / 'out.raw').absolute()
        cmd += ['-raw', f'{raw_file}']
        cmd += self.flags

        # return command and corresponding raw file
        return [cmd], raw_file

    def hspice_cmds(self, tb_file):
        # build up the simulation command
        sim_cmd = []
        sim_cmd += ['hspice']
        sim_cmd += ['-i', f'{tb_file}']
        out_file = (Path(self.directory) / 'out.raw').absolute()
        sim_cmd += ['-o', f'{out_file}']
        sim_cmd += self.flags

        # build up the conversion command
        conv_cmd = []
        conv_cmd += ['converter']
        conv_cmd += ['-t', 'PSF']
        tr0_file = out_file.with_suffix(out_file.suffix + '.tr0')
        conv_cmd += ['-i', f'{tr0_file}']
        psf_file = (Path(self.directory) / 'out.psf').absolute()
        conv_cmd += ['-o', f'{psf_file.with_suffix("")}']
        conv_cmd += ['-a']

        # return command and corresponding raw file
        return [sim_cmd, conv_cmd], psf_file
