import os
from pathlib import Path
from copy import copy
import magma as m
import fault
import hwtypes
import numpy as np
from fault.target import Target
from fault.spice import SpiceNetlist
from fault.nutascii_parse import nutascii_parse
from fault.psf_parse import psf_parse
from fault.subprocess_run import subprocess_run
from fault.pwl import pwc_to_pwl
from fault.actions import Poke, Expect, Delay, Print, Read
from fault.select_path import SelectPath
from fault.background_poke import process_action_list


# define a custom error for A2D conversion to make it easier
# to catch this specific issue (for example, in adapting
# tests based on the previous test result)
class A2DError(Exception):
    pass

# edge finder is used for measuring phase, freq, etc.
class EdgeNotFoundError(Exception):
    pass

class CompiledSpiceActions:
    def __init__(self, pwls, checks, prints, reads, stop_time, saves):
        self.pwls = pwls
        self.checks = checks
        self.prints = prints
        self.reads = reads
        self.stop_time = stop_time
        self.saves = saves


class SpiceTarget(Target):
    def __init__(self, circuit, directory="build/", simulator='ngspice',
                 vsup=1.0, rout=1, model_paths=None, sim_env=None,
                 t_step=None, clock_step_delay=5e-9, t_tr=0.2e-9, vil_rel=0.4,
                 vih_rel=0.6, rz=1e9, conn_order='alpha', bus_delim='<>',
                 bus_order='descend', flags=None, ic=None,
                 disp_type='on_error'):
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

        disp_type: 'on_error', 'realtime'.  If 'on_error', only print if there
                   is an error.  If 'realtime', print out STDOUT as lines come
                   in, then print STDERR after the process completes.
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
        self.ic = ic if ic is not None else {}
        self.disp_type = disp_type

        # place for saving expects that were "save_for_later"
        self.saved_for_later = []

    def run(self, actions):
        # expand background pokes into regular pokes
        actions = process_action_list(actions, self.clock_step_delay)

        # compile the actions
        comp = self.compile_actions(actions)

        # write the testbench
        tb_file = self.write_test_bench(comp)

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
            res = subprocess_run(sim_cmd, cwd=self.directory, env=self.sim_env,
                           disp_type=self.disp_type)
            #print(res.stdout)
            stderr = res.stderr.strip()
            if stderr != '':
                print('Stderr from spice simulator:')
                print(stderr)

        # process the results
        if self.simulator in {'ngspice', 'spectre'}:
            results = nutascii_parse(raw_file)
        elif self.simulator in {'hspice'}:
            results = psf_parse(raw_file)
        else:
            raise NotImplementedError(self.simulator)

        #import matplotlib.pyplot as plt
        #print(results.keys())
        #print('HELLO')
        #in_ = results['in_']
        #out = results['out']
        #plt.plot(in_.x, in_.y, '-o')
        #plt.plot(out.x, out.y, '-o')
        #plt.grid()
        #plt.show()

        # print results
        self.print_results(results=results, prints=comp.prints)

        # set values on reads
        self.process_reads(results, comp.reads)

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
            bit_action.port = m.BitType(name=self.bit_from_bus(action.port, k))
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
        reads = []
        saves = set()

        # expand buses as needed
        _actions = []
        for action in actions:
            if isinstance(action, (Poke, Expect, Read)) \
               and isinstance(action.port, m.BitsType):
                _actions += self.expand_bus(action)
            elif (isinstance(action, (Poke, Expect, Read))
                  and isinstance(action.port.name, m.ref.ArrayRef)):
                action.port = self.select_bit_from_bus(action.port)
                _actions.append(action)
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
                elif isinstance(action.port, m.BitType):
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
                    t += self.clock_step_delay
                else:
                    t += action.delay
            elif isinstance(action, Expect):
                checks.append((t, action))
                saves.add(f'{action.port.name}')
            elif isinstance(action, Print):
                prints.append((t, action))
                for port in action.ports:
                    saves.add(f'{port.name}')
            elif isinstance(action, Read):
                reads.append((t, action))
                saves.add(f'{action.port.name}')
                # phase could be relative to another signal
                if 'ref' in action.params:
                    if isinstance(action.params['ref'].name, m.ref.ArrayRef):
                        ref = self.select_bit_from_bus(action.params['ref'])
                        action.params['ref'] = ref
                    saves.add(f'{action.params["ref"].name}')
            elif isinstance(action, Delay):
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
        return CompiledSpiceActions(
            pwls=pwls,
            checks=checks,
            prints=prints,
            reads=reads,
            stop_time=t,
            saves=saves
        )

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
        if self.bus_delim == '<>':
            return f'{port}<{k}>'
        elif self.bus_delim == '[]':
            return f'{port}[{k}]'
        elif self.bus_delim == '_':
            return f'{port}_{k}'
        else:
            raise Exception(f'Unknown bus delimeter: {self.bus_delim}')

    def select_bit_from_bus(self, port):
        # The default way magma deals with naming one pin of a bus
        # does not match our spice convention. We need to get the
        # name of the original bus and index it ourselves.
        bus_name = port.name.array.name
        bus_index = port.name.index
        bit_name = self.bit_from_bus(bus_name, bus_index)
        new_port = m.BitType(name=bit_name)
        return new_port


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

    def write_test_bench(self, comp, tb_file=None):
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

        # save signals that need to be saved
        netlist.probe(*comp.saves)

        # specify initial conditions if needed
        ic = {}
        for key, val in self.ic.items():
            if isinstance(key, SelectPath):
                ic[f'X0.{key.spice_path}'] = val
            else:
                ic[f'{key}'] = val
        netlist.ic(ic)

        # specify the transient analysis
        t_step = (self.t_step if self.t_step is not None
                  else comp.stop_time / 1000)
        uic = self.ic != {}
        netlist.tran(t_step=t_step, t_stop=comp.stop_time, uic=uic)

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
                raise A2DError(f'Invalid logic level: {value}.')

        if action.save_for_later:
            # save the value and don't check
            self.saved_for_later.append(value)
            return

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

    def impl_print(self, results, time, action):
        # get port values
        port_values = [results[f'{port.name}'](time) for port in action.ports]
        # print formatted output
        print(action.format_str.format(*port_values))

    def print_results(self, results, prints):
        for print_ in prints:
            self.impl_print(results=results, time=print_[0], action=print_[1])

    def process_reads(self, results, reads):
        for time, read in reads:
            res = results[f'{read.port.name}']
            if read.style == 'single':
                value = res(time)
                if type(value) == np.ndarray:
                    value = value.tolist()
                read.value = value
            elif read.style == 'edge':
                value = self.find_edge(res.x, res.y, time, **read.params)
                read.value = value
            elif read.style == 'phase':
                assert 'ref' in read.params, 'Phase read requires reference signal param'
                res_ref = results[f'{read.params["ref"].name}']
                ref = self.find_edge(res_ref.x, res_ref.y, time, count=2)
                before_cycle_end = self.find_edge(res.x, res.y, time + ref[0])
                fraction = 1 + before_cycle_end[0] / (ref[0] -ref[1])
                # TODO multiply by 2pi?
                read.value = fraction
            else:
                raise NotImplementedError(f'Unknown read style "{read.style}"')

    def find_edge(self, x, y, t_start, height=None, forward=False, count=1, rising=True):
        '''
        Search through data (x,y) starting at time t_start for when the
        waveform crosses height (defaut is ???). Searches backwards by
        default (frequency now is probably based on the last few edges?)
        '''

        if height is None:
            # default comes out to 0.5
            height = self.vsup * (self.vih_rel + self.vil_rel) / 2

        # deal with `rising` and `forward`
        # normally a low-to-high finder
        if (rising ^ forward):
            y = [(-1*z + 2*height) for z in y]
        direction = 1 if forward else -1
        # we want to start on the far side of the interval containing t_start
        # to make sure we catch any edge near t_start
        side = 'left' if forward else 'right'

        start_index = np.searchsorted(x, t_start, side=side)
        if start_index == len(x):
            # happens when forward=False and the edge find is the end of the sim
            start_index -= 1

        i = start_index
        edges = []
        while len(edges) < count:
            # move until we hit low
            while y[i] > height:
                i += direction
                if i < 0 or i >= len(y):
                    msg = f'only {len(edges)} of requested {count} edges found'
                    raise EdgeNotFoundError(msg)
            # now move until we hit the high
            while y[i] <= height:
                i += direction
                if i < 0 or i >= len(y):
                    msg = f'only {len(edges)} of requested {count} edges found'
                    raise EdgeNotFoundError(msg)


            # TODO: there's an issue because of the discrepancy between the requested
            # start time and actually staring at the nearest edge

            # the crossing happens from i to i+1
            fraction = (height-y[i]) / (y[i-direction]-y[i])
            t = x[i] + fraction * (x[i+1] - x[i])
            if t==t_start:
                print('EDGE EXACTLY AT EDGE FIND REQUEST')
            edges.append(t-t_start)
        return edges

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
