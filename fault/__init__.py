from .real_type import RealIn, RealOut, RealKind, RealType
from .elect_type import ElectIn, ElectOut, ElectKind, ElectType
from .tester import Tester
from .power_tester import PowerTester
from .value import Value, AnyValue, UnknownValue, HiZ
import fault.random
from .symbolic_tester import SymbolicTester
from .verilogams import VAMSWrap
from .tester_samples import (SRAMTester, InvTester, BufTester,
                             NandTester, NorTester)
from .random import random_bit, random_bv
from .util import clog2
from .spice_target import A2DError


class WrappedVerilogInternalPort:
    def __init__(self, path: str, type_):
        """
        path: <instance_name>.<port_name> (can nest instances)

        type_: magma type of the signal (e.g. m.Bits(2))
        """
        self.path = path
        self.type_ = type_
