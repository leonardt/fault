import os
import logging
from pathlib import Path
import subprocess
import fault.actions
import magma as m
import re
from fault.user_cfg import FaultConfig
from fault.target import Target
from fault.spice import SpiceNetlist


class SpiceTarget(Target):
    def __init__(self, circuit, directory="build/", simulator='ngspice',
                 vsup=1.0, rout=1, model_paths=None, sim_env=None,
                 t_step=None, clock_step_delay=5, t_tr=0.2e-9, vil_rel=0.4,
                 vih_rel=0.6, rz=1e9, flags=None):
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
        self.sim_env = (sim_env if sim_env is not None
                        else FaultConfig().get_sim_env())
        self.t_step = t_step
        self.clock_step_delay = clock_step_delay
        self.t_tr = t_tr
        self.vil_rel = vil_rel
        self.vih_rel = vih_rel
        self.rz = rz
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
            res = self.subprocess_run(sim_cmd)
            assert not res.returncode, f'Error running simulator: {self.simulator}'  # noqa

        # process the results
        if self.simulator in {'ngspice', 'spectre'}:
            results = self.get_nutascii_results(raw_file)
        elif self.simulator in {'hspice'}:
            results = self.get_psf_results(raw_file)
        else:
            raise NotImplementedError(self.simulator)

        # process results
        self.check_results(results=results, checks=checks)

    def stim_to_pwl(self, stim, stop_time, init_val=0):
        # add initial value if necessary
        if stim[0][0] != 0:
            stim = stim.copy()
            stim.insert(0, (0, init_val))

        # then create piecewise-constant waveform
        retval = [stim[0]]
        for k in range(1, len(stim)):
            t_prev, v_prev = stim[k - 1]
            t_curr, v_curr = stim[k]

            retval += [(t_curr, v_prev)]
            retval += [(t_curr + self.t_tr, v_curr)]

        # add final value
        retval += [(stop_time, stim[-1][1])]

        # return new waveform
        return retval

    def compile_actions(self, actions):
        # initialize
        t = 0
        stim_dict = {}
        checks = []

        # loop over actions handling pokes, expects, and delays
        for action in actions:
            if isinstance(action, fault.actions.Poke):
                # add port to stimulus dictionary if needed
                if action.port.name not in stim_dict:
                    stim_dict[action.port.name] = ([], [])
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
                stim_dict[action.port.name][0].append((t, stim_v))
                stim_dict[action.port.name][1].append((t, stim_s))
                # increment time
                t += self.clock_step_delay * 1e-9
            elif isinstance(action, fault.actions.Expect):
                checks.append((t, action))
            elif isinstance(action, fault.actions.Delay):
                t += action.time
            else:
                raise NotImplementedError(action)

        # refactor stimulus voltages to PWL
        pwls = {name: (self.stim_to_pwl(stim=stim[0], stop_time=t),
                       self.stim_to_pwl(stim=stim[1], stop_time=t, init_val=1))
                for name, stim in stim_dict.items()}

        # return PWL waveforms, checks to be performed, and stop time
        return pwls, checks, t

    @staticmethod
    def pwl_str(pwl):
        return ' '.join(f'{t} {v}' for t, v in pwl)

    def write_test_bench(self, pwls, stop_time, tb_file=None):
        # create a new netlist
        netlist = SpiceNetlist()
        netlist.comment('Automatically generated file.')

        # add include files
        for file_ in self.model_paths:
            netlist.include(file_)

        # instantiate the DUT
        dut_name = f'{self.circuit.name}'
        dut_io = [f'{port}' for port in self.circuit.IO.ports]
        netlist.instantiate(dut_name, *dut_io)

        # define the switch model
        inout_sw_mod = 'inout_sw_mod'
        netlist.start_subckt(inout_sw_mod, 'sw_p', 'sw_n', 'ctl_p', 'ctl_n')
        if self.simulator == 'ngspice':
            sw_mod_name = '__inout_sw_mod'
            netlist.model(mod_name=sw_mod_name, mod_type='sw', vt=0.5, vh=0.2,
                          ron=self.rout, roff=self.rz)
            netlist.switch('sw_p', 'sw_n', 'ctl_p', 'ctl_n',
                           mod_name=sw_mod_name, default='ON')
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
            netlist.println('.control', 'run', 'set filetype=ascii', 'write',
                            'exit', '.endc')
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

    def get_nutascii_results(self, raw_file):
        # import dependencies (hidden here to avoid making numpy/scipy
        # a required dependency)
        import numpy as np
        from scipy.interpolate import interp1d

        # parse the file
        section = None
        variables = []
        values = []
        with open(raw_file, 'r') as f:
            for line in f:
                # split line into tokens
                tokens = line.strip().split()
                if len(tokens) == 0:
                    continue

                # change section mode if needed
                if tokens[0] == 'Values:':
                    section = 'Values'
                    tokens = tokens[1:]
                elif tokens[0] == 'Variables:':
                    section = 'Variables'
                    tokens = tokens[1:]

                # parse data in a section-dependent manner
                if section == 'Variables' and len(tokens) >= 2:
                    # sanity check
                    assert int(tokens[0]) == len(variables), 'Out of sync while parsing variables.'  # noqa
                    # add variable
                    variables.append(tokens[1])
                elif section == 'Values':
                    # start a new list if needed
                    for token in tokens:
                        # special handling for first entry
                        if not values or len(values[-1]) == len(variables):
                            # sanity check
                            assert int(token) == len(values), 'Out of sync while parsing values.'  # noqa
                            # clear the value_start flag and start a new
                            # list of values
                            values.append([])
                            continue
                        else:
                            values[-1].append(float(token))
        # sanity check
        if len(values) > 0:
            assert len(values[-1]) == len(variables), 'Missing values at end of file.'  # noqa

        # get vector of time values
        time_vec = np.array([value[variables.index('time')]
                             for value in values])

        # return a dictionary of time-to-value interpolators
        results = {}
        for k, variable in enumerate(variables):
            # skip time variable -- no need to interpolate time to itself
            if variable == 'time':
                continue

            # create vector values for this variable
            value_vec = np.array([value[k] for value in values])

            # create interpolator
            result = interp1d(time_vec, value_vec, bounds_error=False,
                              fill_value=(value_vec[0], value_vec[-1]))

            # add interpolator to dictionary
            results[variable] = result

        # return results
        return results

    def get_psf_results(self, raw_file):
        # import dependencies (hidden here to avoid making numpy/scipy
        # a required dependency)
        import numpy as np
        from scipy.interpolate import interp1d

        # parse the file
        section = None
        read_mode = None
        variables = []
        values = []
        with open(raw_file, 'r') as f:
            for line in f:
                # split line into tokens and strip quotes
                tokens = line.strip().split()
                tokens = [token.strip('"') for token in tokens]
                if len(tokens) == 0:
                    continue

                # change section mode if needed
                if tokens[0] == 'TRACE':
                    section = 'TRACE'
                    continue
                elif tokens[0] == 'VALUE':
                    section = 'VALUE'
                    continue

                # parse data in a section-dependent manner
                if section == 'TRACE':
                    if tokens[0] == 'group':
                        continue
                    else:
                        variables.append(tokens[0])
                elif section == 'VALUE':
                    for token in tokens:
                        if token == 'END':
                            break
                        elif token == 'TIME':
                            read_mode = 'TIME'
                        elif token == 'group':
                            read_mode = 'group'
                        elif read_mode == 'TIME':
                            values.append((float(token), []))
                            read_mode = None
                        elif read_mode == 'group':
                            values[-1][1].append(float(token))
                        else:
                            raise Exception('Unknown token parsing state.')

        # get vector of time values
        time_vec = np.array([value[0] for value in values])

        # re-name voltage variables for consistency
        renamed = []
        for variable in variables:
            m = re.match(r'[vV]\((\w+)\)', variable)
            if m:
                renamed.append(m.groups(0)[0])
            else:
                renamed.append(variable)

        # return a dictionary of time-to-value interpolators
        results = {}
        for k, variable in enumerate(renamed):
            # create vector values for this variable
            value_vec = np.array([value[1][k] for value in values])

            # create interpolator
            result = interp1d(time_vec, value_vec, bounds_error=False,
                              fill_value=(value_vec[0], value_vec[-1]))

            # add interpolator to dictionary
            results[variable] = result

        # return results
        return results

    @staticmethod
    def display_subprocess_output(result):
        # display both standard output and standard error as INFO, since
        # since some useful debugging info is included in standard error

        to_display = {
            'STDOUT': result.stdout.decode(),
            'STDERR': result.stderr.decode()
        }

        for name, val in to_display.items():
            if val != '':
                logging.info(f'*** {name} ***')
                logging.info(val)

    def subprocess_run(self, args, display=True):
        # Runs a subprocess in the user-specified directory with
        # the user-specified environment.

        logging.info(f"Running command: {' '.join(args)}")
        result = subprocess.run(args, cwd=self.directory,
                                capture_output=True, env=self.sim_env)

        if display:
            self.display_subprocess_output(result)

        return result
