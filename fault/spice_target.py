import os
from pathlib import Path
from copy import copy
import magma as m
import fault
import hwtypes
from fault.target import Target
from fault.spice import SpiceNetlist
from fault.ms_types import RealInOut
from fault.result_parse import nut_parse, hspice_parse, psf_parse
from fault.subprocess_run import subprocess_run
from fault.pwl import pwc_to_pwl
from fault.actions import Poke, Expect, Delay, Print, GetValue, Eval
from fault.select_path import SelectPath
from .fault_errors import A2DError, ExpectError

try:
    from decida.SimulatorNetlist import SimulatorNetlist
    import numpy as np
except ModuleNotFoundError:
    print('Failed to import DeCiDa or Numpy for SpiceTarget.')


class CompiledSpiceActions:
    def __init__(self, pwls, checks, prints, stop_time, saves, gets):
        self.pwls = pwls
        self.checks = checks
        self.prints = prints
        self.stop_time = stop_time
        self.saves = saves
        self.gets = gets


def DeclareFromSpice(file_name, subckt_name=None, mode='digital'):
    # parse the netlist
    spice_model_path = Path(file_name).resolve()
    parser = SimulatorNetlist(f'{spice_model_path}')

    # use the first subcircuit defined if none is specified
    if subckt_name is None:
        subckts = parser.get('subckts')
        if len(subckts) == 0:
            raise Exception(f'Could not find any circuit definitions in {file_name}.')  # noqa
        else:
            subckt_name = parser.get('subckts')[0]

    # get the port list for the subcircuit
    search_name = f'{subckt_name}'.lower()
    ports = parser.get_subckt(search_name, detail='ports')

    # declare the circuit and return it
    args = []
    args += [subckt_name]
    for port in ports:
        args += [f'{port}']
        if mode == 'digital':
            args += [m.BitInOut]
        elif mode == 'analog':
            args += [RealInOut]
        else:
            raise ValueError(f'Unknown mode: {mode}')

    # Declare spice circuit and specify source location
    circuit = m.DeclareCircuit(*args)
    circuit.spice_model_path = spice_model_path

    # Return the circuit
    return circuit


MONTE_CARLO_SPECTRE = '''\
mc1 montecarlo variations={variations} savefamilyplots=yes numruns={numruns} {{
    tran1 tran start=0 stop={stop}
}}
'''


class SpiceTarget(Target):
    def __init__(self, circuit, directory="build/", simulator='ngspice',
                 vsup=1.0, rout=1, model_paths=None, sim_env=None,
                 t_step=None, clock_step_delay=5, t_tr=0.2e-9, vil_rel=0.4,
                 vih_rel=0.6, rz=1e9, conn_order='parse', bus_delim='<>',
                 bus_order='descend', flags=None, ic=None, cap_loads=None,
                 disp_type='on_error', mc_runs=0, mc_variations='all',
                 vol_rel=0.1, voh_rel=0.9, no_run=False, uic=None):
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

        bus_delim: '<>', '[]', or '_' indicating bus styles "a<3>", "b[2]",
                   c_1.

        bus_order: 'descend' or 'ascend', indicating whether buses are
                   order from largest to smallest or smallest to largest,
                   respectively.

        flags: List of additional arguments that should be passed to the
               simulator.

        cap_loads: Dictionary mapping device ports to capacitive loads
                   that should be added to those ports.

        disp_type: 'on_error', 'realtime'.  If 'on_error', only print if there
                   is an error.  If 'realtime', print out STDOUT as lines come
                   in, then print STDERR after the process completes.

        mc_runs: Number of Monte-Carlo runs for the simulation (defaults to
                 zero, meaning that Monte-Carlo simulation will not be used.

        mc_variations: 'process', 'mismatch', or 'all'.  Defaults to 'all'.

        vol_rel: Falling edge threshold as a fraction of vsup

        voh_rel: Rising edge threshold as a fraction of vsup

        no_run: If True, don't actually run the simulation.

        uic: If True, use initial conditions.  If not specified, "uic" is True
             if any initial conditions are specified, and is false otherwise.
        """
        # call the super constructor
        super().__init__(circuit)

        # sanity check
        if simulator not in {'ngspice', 'spectre', 'hspice'}:
            raise ValueError(f'Unsupported simulator {simulator}')

        # set model_paths
        if model_paths is None:
            model_paths = []
        if hasattr(circuit, 'spice_model_path'):
            model_paths = [f'{circuit.spice_model_path}'] + model_paths

        # make directory if needed
        os.makedirs(directory, exist_ok=True)

        # save settings
        self.directory = directory
        self.simulator = simulator
        self.vsup = vsup
        self.rout = rout
        self.model_paths = model_paths
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
        self.ic = ic if ic is not None else {}
        self.cap_loads = cap_loads if cap_loads is not None else {}
        self.disp_type = disp_type
        self.mc_variations = mc_variations
        self.mc_runs = mc_runs
        self.vol_rel = vol_rel
        self.voh_rel = voh_rel
        self.no_run = no_run

        # set default for "uic"
        if uic is None:
            if len(self.ic) > 0:
                uic = True
            else:
                uic = False
        self.uic = uic

        # set list of signals to save
        self.saves = set()
        for name, port in self.circuit.interface.ports.items():
            if isinstance(port, m.BitsType):
                for k in range(len(port)):
                    self.saves.add(self.bit_from_bus(name, k))
            else:
                self.saves.add(f'{name}')

    def run(self, actions):
        # compile the actions
        comp = self.compile_actions(actions)

        # write the testbench
        tb_file = self.write_test_bench(comp)

        # generate simulator commands
        if self.simulator == 'ngspice':
            cmd, raw_files = self.ngspice_cmds(tb_file)
        elif self.simulator == 'spectre':
            cmd, raw_files = self.spectre_cmds(tb_file)
        elif self.simulator == 'hspice':
            cmd, raw_files = self.hspice_cmds(tb_file)
        else:
            raise NotImplementedError(self.simulator)

        # run the simulation commands
        if not self.no_run:
            subprocess_run(cmd, cwd=self.directory, env=self.sim_env,
                           disp_type=self.disp_type)

        # process the results
        for raw_file in raw_files:
            if self.simulator in {'ngspice'}:
                results = nut_parse(raw_file)
            elif self.simulator in {'spectre'}:
                results = psf_parse(raw_file)
            elif self.simulator in {'hspice'}:
                results = hspice_parse(raw_file)
            else:
                raise NotImplementedError(self.simulator)

            # print results
            self.print_results(results=results, prints=comp.prints)

            # implement all of the gets
            self.impl_all_gets(results=results, gets=comp.gets)

            # check results
            self.check_results(results=results, checks=comp.checks)

    def expand_bus(self, action):
        # define bit-access function for the action's value
        # this is needed at the moment because fault.HiZ cannot
        # be used in a BitVector -- but it is still a common
        # use case to set a whole bus to HiZ
        def get_value_at_bit(k):
            if action.value is fault.HiZ:
                return fault.HiZ
            else:
                # this should work both for BitVectors and integers
                value = hwtypes.BitVector[len(action.port)](action.value)
                return value[k]

        # return a list of single-bit pokes
        retval = []

        # for each bit...
        for k in range(len(action.port)):
            # create a new action corresponding to that single bit
            # copy is used to preserve any other properties of
            # the action that are not bit-index specific (e.g.,
            # "strict" for expect).  Still, it's a bit hacky and
            # there is likely a better way...
            bit_action = copy(action)
            bit_action.port = m.Bit(name=self.bit_from_bus(action.port, k))
            bit_action.value = get_value_at_bit(k)
            retval.append(bit_action)

        # return the new list of expanded-out actions
        return retval

    def compile_actions(self, actions):
        # initialize
        t = 0
        pwc_dict = {}
        checks = []
        prints = []
        gets = []

        # expand buses as needed
        _actions = []
        for action in actions:
            if isinstance(action, (Poke, Expect)) \
               and isinstance(action.port, m.Bits):
                _actions += self.expand_bus(action)
            else:
                _actions.append(action)
        actions = _actions

        # loop over actions handling pokes, expects, and delays
        for action in actions:
            if isinstance(action, Poke):
                # add port to stimulus dictionary if needed
                action_port_name = f'{action.port.name}'
                if action_port_name not in pwc_dict:
                    pwc_dict[action_port_name] = ([], [])
                # determine the stimulus value, performing a digital
                # to analog conversion if needed and controlling
                # the output switch as needed
                if action.value is fault.HiZ:
                    stim_v = 0
                    stim_s = 0
                elif isinstance(action.port, m.Bit):
                    stim_v = self.vsup if action.value else 0
                    stim_s = 1
                else:
                    stim_v = action.value
                    stim_s = 1
                # add the value to the list of actions
                pwc_dict[action_port_name][0].append((t, stim_v))
                pwc_dict[action_port_name][1].append((t, stim_s))
                # increment time if desired
                if action.delay is None:
                    t += self.clock_step_delay * 1e-9
                else:
                    t += action.delay
            elif isinstance(action, Expect):
                checks.append((t, action))
            elif isinstance(action, Print):
                prints.append((t, action))
            elif isinstance(action, GetValue):
                gets.append((t, action))
            elif isinstance(action, Delay):
                t += action.time
            elif isinstance(action, Eval):
                continue
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
        return CompiledSpiceActions(
            pwls=pwls,
            checks=checks,
            prints=prints,
            gets=gets,
            stop_time=t,
            saves=self.saves
        )

    @staticmethod
    def pwl_str(pwl):
        return ' '.join(f'{t} {v}' for t, v in pwl)

    def get_ordered_ports(self):
        if self.conn_order == 'alpha':
            return self.get_alpha_ordered_ports()
        elif self.conn_order == 'parse':
            return self.get_parse_ordered_ports()
        else:
            raise Exception(f'Unknown conn_order: {self.conn_order}.')

    def bit_from_bus(self, port, k):
        if self.bus_delim == '<>':
            return f'{port}<{k}>'
        elif self.bus_delim == '[]':
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
            if isinstance(port, (m.Bit, fault.RealType, fault.ElectType)):
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

    def get_parse_ordered_ports(self):
        for path in self.model_paths:
            parser = SimulatorNetlist(f'{path}')
            search_name = f'{self.circuit.name}'.lower()
            if search_name in parser.get('subckts'):
                return parser.get_subckt(search_name, detail='ports')
        else:
            raise Exception(f'Could not find subcircuit {self.circuit.name}.')

    def write_test_bench(self, comp, tb_file=None):
        # create a new netlist
        netlist = SpiceNetlist()
        netlist.comment('Automatically generated file.')

        # add include files
        for file_ in self.model_paths:
            netlist.include(Path(file_).resolve())

        # instantiate the DUT
        dut_name = f'{self.circuit.name}'
        netlist.instantiate(dut_name, *self.get_ordered_ports())

        # add a capacitance to some ports if specified
        for port, val in self.cap_loads.items():
            netlist.capacitor(f'{port.name}', '0', val)

        # define the switch model
        inout_sw_mod = 'inout_sw_mod'
        netlist.start_subckt(inout_sw_mod, 'sw_p', 'sw_n', 'ctl_p', 'ctl_n')
        if self.simulator == 'ngspice':
            a = (1 / self.rout) - (1 / self.rz)
            b = (1 / self.rz)
            netlist.println(f"Gs sw_p sw_n cur='V(sw_p, sw_n)*({a}*V(ctl_p, ctl_n)+{b})'")  # noqa
        elif self.simulator in {'spectre', 'hspice'}:
            netlist.vcr('sw_p', 'sw_n', 'ctl_p', 'ctl_n',
                        pwl=[(0, self.rz), (1, self.rout)])
        netlist.end_subckt()

        # write stimuli lines
        for name, (pwl_v, pwl_s) in comp.pwls.items():
            # instantiate switch between voltage source and DUT
            vnet = f'__{name}_v'
            snet = f'__{name}_s'
            netlist.instantiate('inout_sw_mod', vnet, name, snet, '0')

            # instantiate voltage source connected through switch
            netlist.voltage(vnet, '0', pwl=pwl_v)
            netlist.voltage(snet, '0', pwl=pwl_s)

        # specify initial conditions if needed
        ic = {}
        for key, val in self.ic.items():
            if isinstance(key, SelectPath):
                ic[f'X0.{key.spice_path}'] = val
            else:
                ic[f'{key}'] = val
        if ic != {}:
            netlist.ic(ic)

        # specify the transient analysis
        t_step = (self.t_step if self.t_step is not None
                  else comp.stop_time / 1000)
        if self.simulator in {'hspice', 'ngspice'}:
            netlist.tran(t_step=t_step, t_stop=comp.stop_time, uic=self.uic)

        # generate control statement
        if self.simulator == 'ngspice':
            netlist.start_control()
            netlist.println('run')
            netlist.println('set filetype=binary')
            netlist.println('write')
            netlist.println('exit')
            netlist.end_control()
        elif self.simulator == 'hspice':
            netlist.options('csdf')

        # write end of file
        if self.simulator == 'spectre':
            netlist.probe(*comp.saves, wrap=True)
            if self.mc_runs == 0:
                netlist.tran(t_step=t_step, t_stop=comp.stop_time, uic=self.uic)
            else:
                netlist.println('simulator lang=spectre')
                netlist.print(MONTE_CARLO_SPECTRE.format(
                    variations=self.mc_variations,
                    numruns=self.mc_runs,
                    stop=comp.stop_time
                ))
        elif self.simulator == 'hspice':
            netlist.probe(*comp.saves, wrap=True, antype='TRAN')
            netlist.end_file()
        elif self.simulator == 'ngspice':
            netlist.probe(*comp.saves, wrap=True)
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
        if isinstance(action.port, m.Bit):
            if value <= self.vil_rel * self.vsup:
                value = 0
            elif value >= self.vih_rel * self.vsup:
                value = 1
            else:
                raise A2DError(f'Invalid logic level: {value}.')

        # determine the condition and error body
        err_hdr = ''
        err_hdr += f'Failed checking port {action.port.name}'
        err_hdr += f' at time {time:0.3e}'
        if action.traceback is not None:
            err_hdr += f' with traceback {action.traceback}'

        # implement the requested check
        err_msg = None
        if action.above is not None:
            if action.below is not None:
                if not (action.above <= value <= action.below):
                    err_msg = f'Expected {action.above} to {action.below}, got {value}'  # noqa
            else:
                if not (action.above <= value):
                    err_msg = f'Expected above {action.above}, got {value}.'
        else:
            if action.below is not None:
                if not (value <= action.below):
                    err_msg = f'Expected below {action.below}, got {value}.'
            else:
                if not (value == action.value):
                    err_msg = f'Expected {action.value}, got {value}.'

        # raise exception if there was an error
        if err_msg is not None:
            raise ExpectError(f'{err_hdr}.  {err_msg}.')

    def check_results(self, results, checks):
        for check in checks:
            self.impl_expect(results=results, time=check[0], action=check[1])

    def impl_print(self, results, time, action):
        # get port values
        port_values = [results[f'{port.name}'](time) for port in action.ports]
        # print formatted output
        print(action.format_str.format(*port_values))

    def print_results(self, results, prints):
        for print_ in prints:
            self.impl_print(results=results, time=print_[0], action=print_[1])

    def impl_all_gets(self, results, gets):
        for get in gets:
            self.impl_get(results=results, time=get[0], action=get[1])

    def impl_get(self, results, time, action):
        # get port values
        port_value = results[f'{action.port.name}'](time)
        # write value back to action
        action.value = port_value

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
        return cmd, [raw_file]

    def spectre_cmds(self, tb_file):
        # build up the command
        cmd = []
        cmd += ['spectre']
        cmd += [f'{tb_file}']
        cmd += ['-format', 'psfascii']
        raw_dir = (Path(self.directory) / 'psf').resolve()
        cmd += ['-raw', f'{raw_dir}']
        cmd += self.flags

        # figure out where the PSF results will be stored
        if self.mc_runs == 0:
            raw_files = [raw_dir / 'timeSweep.tran.tran']
        else:
            raw_files = []
            for k in range(0, self.mc_runs + 1):
                raw_file = 'transient1-{:03d}_transient1.tran.tran'.format(k)
                raw_files.append(raw_dir / raw_file)

        # return command and corresponding raw file
        return cmd, raw_files

    def hspice_cmds(self, tb_file):
        # build up the simulation command
        cmd = []
        cmd += ['hspice']
        cmd += ['-i', f'{tb_file}']
        out_file = (Path(self.directory) / 'out.raw').absolute()
        cmd += ['-o', f'{out_file}']
        cmd += self.flags

        # build up the conversion command
        tr0_file = out_file.with_suffix(out_file.suffix + '.tr0')

        # return command and corresponding raw file
        return cmd, [tr0_file]
