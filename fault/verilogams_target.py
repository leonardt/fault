import os
from pathlib import Path
from .system_verilog_target import SystemVerilogTarget


class VerilogAMSTarget(SystemVerilogTarget):
    def __init__(self, circuit, simulator='ncsim', directory='build/',
                 model_paths=None, stop_time=1, vsup=1.0, rout=1, flags=None,
                 include_verilog_libraries=None, **kwargs):
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
        include_verilog_libraries: Additional source files to be compiled
        when building this simulation.
        """

        # save settings
        self.stop_time = stop_time
        self.vsup = vsup
        self.rout = rout

        # save file names that will be written
        self.amscf = 'amscf.scs'

        # update simulator argument
        assert simulator == 'ncsim', 'Only the ncsim simulator is allowed at this time.'  # noqa

        # update flags argument
        flags = flags if flags is not None else []
        model_paths = model_paths if model_paths is not None else []
        for path in model_paths:
            flags += ['-modelpath', f'{path}']

        # update include_verilog_libraries
        include_verilog_libraries = (include_verilog_libraries
                                     if include_verilog_libraries is not None
                                     else [])
        include_verilog_libraries += [self.amscf]

        # call the superconstructor
        super().__init__(circuit=circuit, simulator=simulator, flags=flags,
                         include_verilog_libraries=include_verilog_libraries,
                         directory=directory, **kwargs)

    def run(self, *args, **kwargs):
        # write the AMS control file
        self.write_amscf()

        # then call the super constructor
        super().run(*args, **kwargs)

    def gen_amscf(self):
        return f'''
tranSweep tran stop={self.stop_time}s
amsd {{
    ie vsup={self.vsup} rout={self.rout}
}}'''

    def write_amscf(self):
        with open(self.directory / Path(self.amscf), 'w') as f:
            f.write(self.gen_amscf())
