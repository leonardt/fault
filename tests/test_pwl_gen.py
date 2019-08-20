from fault.pwl import pwc_to_pwl
from math import isclose


def check_pwl_result(meas, expct):
    for k, (a, b) in enumerate(zip(meas, expct)):
        assert isclose(a[0], b[0]), f'Time mismatch at index {k}: {a[0]} vs {b[0]}'  # noqa
        assert isclose(a[1], b[1]), f'Value mismatch at index {k}: {a[1]} vs {b[1]}'  # noqa


def test_spice_target_pwl(t_tr=0.2e-9, t_stop=20e-9):
    def run_test(stim, expct):
        meas = pwc_to_pwl(stim, t_stop, t_tr=t_tr)
        check_pwl_result(meas=meas, expct=expct)

    run_test([(1e-9, 1.2), (10e-9, 3.4), (15e-9, 5.6)],
             [(0, 0), (1e-9, 0), (1.2e-9, 1.2), (10e-9, 1.2), (10.2e-9, 3.4), (15e-9, 3.4), (15.2e-9, 5.6), (20e-9, 5.6)])  # noqa

    run_test([(0, 1.2), (10e-9, 3.4), (15e-9, 5.6)],
             [(0, 1.2), (10e-9, 1.2), (10.2e-9, 3.4), (15e-9, 3.4), (15.2e-9, 5.6), (20e-9, 5.6)])  # noqa
