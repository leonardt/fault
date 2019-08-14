import os
import logging
from pathlib import Path
import subprocess
import fault.actions
import magma as m
from fault.user_cfg import FaultConfig
from fault.target import Target


src_tpl = """\
* Automatically generated testbench

{includes}

.model inout_sw_mod sw vt=0.5 vh=0.2 ron={rout}

Xdut {dut_io} {dut_name}
{stimuli}

.tran {t_step} {stop_time}

.control
run
set filetype=ascii
write
exit
.endc

.end
"""


class SpiceTarget(Target):
    def __init__(self, circuit, directory="build/", simulator='ngspice',
                 vsup=1.0, rout=1, model_paths=None, sim_env=None,
                 t_step=None, clock_step_delay=5, t_tr=0.2e-9, vil_rel=0.4,
                 vih_rel=0.6, flags=None):
        """
        circuit: a magma circuit

        directory: directory to use for generating collateral, buildling, and
                   running simulator

        simulator: "ngspice"

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

        flags: List of additional arguments that should be passed to the
               simulator.
        """
        # call the super constructor
        super().__init__(circuit)

        # sanity check
        if simulator not in {'ngspice'}:
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
        self.flags = flags if flags is not None else []

    def run(self, actions):
        # compile the actions
        pwls, checks, stop_time = self.compile_actions(actions)

        # write the testbench
        tb_file = self.write_test_bench(pwls=pwls, stop_time=stop_time)

        # generate simulator commands
        if self.simulator == 'ngspice':
            sim_cmd, raw_file = self.ngspice_cmd(tb_file)
            err_str = None
        else:
            raise NotImplementedError(self.simulator)

        # run the simulation
        sim_res = self.subprocess_run(sim_cmd + self.flags)
        assert not sim_res.returncode, f'Error running simulator: {self.simulator}'  # noqa
        if err_str is not None:
            assert err_str not in str(sim_res.stdout), f'"{err_str}" found in stdout of {self.simulator}'  # noqa

        # process the results
        if self.simulator == 'ngspice':
            results = self.get_ngspice_results(raw_file)
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

    def write_test_bench(self, pwls, stop_time, tb_file=None, nl='\n'):
        # determine files
        includes = nl.join(f'.include {file_}' for file_ in self.model_paths)

        # determine DUT I/O
        dut_io = [f'{port}' for port in self.circuit.IO.ports]
        dut_io = ' '.join(dut_io)
        dut_name = self.circuit.name

        # write stimuli lines
        stimuli = []
        for k, (name, (pwl_v, pwl_s)) in enumerate(pwls.items()):
            # instantiate switch between voltage source and DUT
            vnet = f'__{name}_v'
            snet = f'__{name}_s'
            stimuli += [f'S{k} {vnet} {name} {snet} 0 inout_sw_mod ON']

            # instantiate voltage source connected through switch
            dc_v_val = pwl_v[0][1]
            pwl_v_str = self.pwl_str(pwl_v)
            stimuli.append(f'Vv{k} {vnet} 0 DC {dc_v_val} PWL({pwl_v_str})')

            # instantiate voltage source controlling switch
            dc_s_val = pwl_s[0][1]
            pwl_s_str = self.pwl_str(pwl_s)
            stimuli.append(f'Vs{k} {snet} 0 DC {dc_s_val} PWL({pwl_s_str})')

        # add newlines between individual entries
        stimuli = nl.join(stimuli)

        # determine the step time
        t_step = self.t_step if self.t_step is not None else stop_time / 1000

        # render SPICE file
        code = src_tpl.format(
            includes=includes,
            dut_io=dut_io,
            dut_name=dut_name,
            stimuli=stimuli,
            rout=self.rout,
            t_step=f'{t_step}',
            stop_time=f'{stop_time}'
        )

        # write spice file
        tb_file = (tb_file if tb_file is not None
                   else Path(self.directory) / f'{self.circuit.name}_tb.sp')
        tb_file = tb_file.absolute()
        with open(tb_file, 'w') as f:
            f.write(code)

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

    def ngspice_cmd(self, tb_file, raw_file=None):
        # set defaults
        raw_file = (raw_file if raw_file is not None
                    else Path(self.directory) / 'out.raw')
        raw_file = Path(raw_file).absolute()

        # build up the command
        cmd = []
        cmd += ['ngspice']
        cmd += ['-b']
        cmd += [f'{tb_file}']
        cmd += ['-r', f'{raw_file}']

        # return command and corresponding raw file
        return cmd, raw_file

    def get_ngspice_results(self, raw_file):
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
                if line.strip() == '':
                    continue
                elif line.strip().lower().startswith('variable'):
                    section = 'variables'
                    continue
                elif line.strip().lower().startswith('value'):
                    section = 'values'
                    continue
                elif section == 'variables':
                    tokens = line.strip().split()
                    variables.append(tokens[1])
                elif section == 'values':
                    tokens = line.strip().split()
                    # start a new list if needed
                    for token in tokens:
                        # special handling for first entry
                        if not values or len(values[-1]) == len(variables):
                            # sanity check
                            assert int(token) == len(values), 'Out of sync while parsing file.'
                            # clear the value_start flag and start a new
                            # list of values
                            values.append([])
                            continue
                        else:
                            values[-1].append(float(token))
        # sanity check
        if len(values) > 0:
            assert len(values[-1]) == len(variables), 'Missing values at end of file.'

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
