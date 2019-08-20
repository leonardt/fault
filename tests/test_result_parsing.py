from fault.psf_parse import psf_parse
from fault.nutascii_parse import nutascii_parse
from math import isclose
from pathlib import Path


def check_spice_result(meas, expct):
    for t, v in expct:
        mint = meas(t)
        assert isclose(mint, v), f'Value mismatch at time {t}: {mint} vs {v}'


def test_psf_parse():
    results = nutascii_parse(Path('tests/data/ngspice.raw').resolve())
    check_spice_result(results['in_'], [(0, 2), (1, 2), (2.5, 3.5), (4, 5),
                                        (5.5, 6.5), (7, 8), (8, 8)])
    check_spice_result(results['out<0>'], [(1, 3), (4, 6), (7, 9)])


def test_spice_target_psf_parse():
    results = psf_parse(Path('tests/data/hspice.psf').resolve())
    check_spice_result(results['in_'], [(0, 2), (1, 2), (2.5, 3.5), (4, 5),
                                        (5.5, 6.5), (7, 8), (8, 8)])
    check_spice_result(results['out<0>'], [(1, 3), (4, 6), (7, 9)])
