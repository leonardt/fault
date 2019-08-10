import shutil


def pytest_sim_params(metafunc, *args):
    # simulators supported by each kind of target
    sims_by_arg = {'system-verilog': ['vcs', 'ncsim', 'iverilog'],
                   'verilog-ams': ['ncsim'],
                   'verilator': [None]}

    # only parameterize if we can actually specify the target type
    # and simulator to use for this particular test
    fixturenames = metafunc.fixturenames
    if 'target' in fixturenames and 'simulator' in fixturenames:
        targets = []
        for arg in args:
            for simulator in sims_by_arg[arg]:
                if simulator is None or shutil.which(simulator):
                    targets.append((arg, simulator))

        metafunc.parametrize("target,simulator", targets)
