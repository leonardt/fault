from fault.spice_target import SpiceTarget
from math import isclose
from pathlib import Path


def check_pwl_result(meas, expct):
    for k, (a, b) in enumerate(zip(meas, expct)):
        assert isclose(a[0], b[0]), f'Time mismatch at index {k}: {a[0]} vs {b[0]}'  # noqa
        assert isclose(a[1], b[1]), f'Value mismatch at index {k}: {a[1]} vs {b[1]}'  # noqa


def test_spice_target_pwl(t_tr=0.2e-9, t_stop=20e-9):
    obj = SpiceTarget(None, clock_step_delay=5, t_tr=t_tr)

    def run_test(stim, expct):
        meas = obj.stim_to_pwl(stim, t_stop)
        check_pwl_result(meas=meas, expct=expct)

    run_test([(1e-9, 1.2), (10e-9, 3.4), (15e-9, 5.6)],
             [(0, 0), (1e-9, 0), (1.2e-9, 1.2), (10e-9, 1.2), (10.2e-9, 3.4), (15e-9, 3.4), (15.2e-9, 5.6), (20e-9, 5.6)])  # noqa

    run_test([(0, 1.2), (10e-9, 3.4), (15e-9, 5.6)],
             [(0, 1.2), (10e-9, 1.2), (10.2e-9, 3.4), (15e-9, 3.4), (15.2e-9, 5.6), (20e-9, 5.6)])  # noqa


def check_spice_result(meas, expct):
    for t, v in expct:
        mint = meas(t)
        assert isclose(mint, v), f'Value mismatch at time {t}: {mint} vs {v}'


def test_spice_target_ngspice_parse():
    obj = SpiceTarget(None)
    results = obj.get_ngspice_results(Path('tests/data/ngspice.raw').resolve())

    check_spice_result(results['in_'], [(0, 2), (1, 2), (2.5, 3.5), (4, 5),
                                        (5.5, 6.5), (7, 8), (8, 8)])
    check_spice_result(results['out'], [(1, 3), (4, 6), (7, 9)])
