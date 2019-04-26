import typing as tp
import random
import itertools as it
from hwtypes import AbstractBitVector, AbstractBit
from hwtypes import BitVector, Bit
from hwtypes import z3BitVector, z3Bit
from collections.abc import Mapping
import z3

def constrained_random_bv(width, pred):
    while True:
        randval = random_bv(width)
        if pred(randval):
            return randval

def random_bv(width):
    return BitVector[width](random.randint(0, (1 << width) - 1))

def random_bit():
    return Bit(random.randint(0, 1))

class HashableDict(Mapping):
    def __init__(self, d=None):
        if d is None:
            d = dict()
        self._d = dict(d)
        self._hash = None

    def __getitem__(self, idx):
        return self._d[idx]

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(frozenset(self.items()))
        return self._hash

    def __eq__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        else:
            return self._d == dict(other)

    def __ne__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        else:
            return self._d != dict(other)

    def __repr__(self):
        return f'{type(self).__name__}({repr(self._d)})'

def _model_to_hashdict(v_map, model):
    d = {}
    for k,v in v_map.items():
        if isinstance(v, AbstractBitVector):
            d[k] = BitVector[v.size](model[v.value].as_long())
        elif isinstance(v, AbstractBit):
            d[k] = Bit(bool(model[v.value]))
        else:
            raise TypeError()
    return HashableDict(d)

class ConstrainedRandomGenerator:
    def __init__(self,
            alpha_min : float = 0.1,
            epoch_length : int = 6,
            call_timeout : int = 10,
            ):
        '''
        alpha_min : Min hit rate before beginning a new epoch,
        epoch_length : Number of rounds in a epoch, smaller will produce more random but be slower
        call_timout : per call timeout
        for full details see:
        https://people.eecs.berkeley.edu/~ksen/papers/smtsampler.pdf
        '''
        self.alpha_min = alpha_min
        self.epoch_length = epoch_length
        self.call_timeout = call_timeout

    def _init_solver(self):
        self.solver = z3.Optimize()
        self.solver.set('timeout', self.call_timeout)


    def __call__(
            self,
            v_map : tp.Mapping[str, tp.Optional[int]],
            pred : tp.Callable[..., AbstractBit],
            N : int,
            ) -> tp.AbstractSet[tp.Mapping[str, BitVector]]:
        '''
        V_map: map of labels to bitvector sizes, size is None indicates a Bit
        pred: function with signiture (v : AbstractBitVector[w] for v,w in V_map.items()) -> AbstractBit
        N: Numbers of samples
        '''
        self._init_solver()
        solver = self.solver
        alpha_min = self.alpha_min
        epoch_length = self.epoch_length

        v_map = {k : z3BitVector[w]() if w is not None else z3Bit() for k,w in v_map.items()}
        solutions = set()
        seen = set()

        while len(solutions) < N:
            seed = self._generate_random(v_map, seen)
            seen.add(seed)
            init = self._find_closet(v_map, pred, seed)

            if init is None:
                break

            solutions.add(init)
            seen.add(init)

            if epoch_length <= 0:
                continue

            S1 = self._compute_neighbors(v_map, pred, init, seen)

            seen |= S1
            solutions |= S1

            Sk = S1
            alpha = 1
            for k in range(1, epoch_length+1):
                if alpha < alpha_min or len(solutions) >= N:
                    break
                Sk, alpha, seen = self._combine(v_map, Sk, S1, init, seen, pred, N-len(solutions))
                solutions |= Sk

        return solutions

    def _generate_random(self, v_map, seen):
        while True:
            assignment = {}
            for k,v in v_map.items():
                if isinstance(v, AbstractBitVector):
                    assignment[k] = random_bv(v.size)
                elif isinstance(v, AbstractBit):
                    assignment[k] = random_bit()
                else:
                    TypeError()

            assignment = HashableDict(assignment)
            if assignment not in seen:
                return assignment

    def _find_closet(self, v_map, pred, seed):
        solver = self.solver
        solver.push()
        solver.set('timeout', self.call_timeout*4)
        solver.add(pred(**v_map).value)
        for k,v in v_map.items():
            assignment = seed[k]
            if isinstance(v, AbstractBitVector):
                for i in range(v.size):
                    solver.add_soft((v[i:i+1] == assignment[i:i+1]).value)
            elif isinstance(v, AbstractBit):
                solver.add_soft((v == assignment).value)
            else:
                raise TypeError()
        if solver.check() == z3.sat:
            model = solver.model()
            solver.pop()
            return _model_to_hashdict(v_map, model)
        else:
            return None

    def _compute_neighbors(self, v_map, pred, init, seen):
        conditons = []
        for k,v in v_map.items():
            if isinstance(v, AbstractBitVector):
                for i in range(v.size):
                    conditons.append(v[i] == init[k][i])
            elif isinstance(v, AbstractBit):
                conditons.apppend(v == init[k])
            else:
                raise TypeError()
        S1 = set()
        for c in conditons:
            S1 |= self._find_neighbor(v_map, pred, c, conditons)
        return S1

    def _find_neighbor(self, v_map, pred, c, conditons):
        solver = self.solver
        solver.push()
        solver.set('timeout', self.call_timeout)
        solver.add(pred(**v_map).value)
        solver.add((~c).value)
        solver.push()
        for c_ in  conditons:
            if c_ is not c:
                solver.add_soft(c_.value)
        res = solver.check()

        if res == z3.unknown:
            solver.pop()
            solver.set('timeout', self.call_timeout*2)
            if solver.check() == z3.sat:
                model = solver.model()
                solver.pop()
                return {_model_to_hashdict(v_map, model)}
            else:
                solver.pop()
                return set()
        elif res == z3.sat:
            model = solver.model()
            solver.pop()
            solver.pop()
            return {_model_to_hashdict(v_map, model)}
        else:
            solver.pop()
            solver.pop()
            return set()

    def _combine(self, v_map, Sk, S1, init, seen, pred, n):
        valid = 0
        checks = 0
        Sk1 = set()
        for sa,sb in it.product(Sk, S1):
            if valid >= n:
                break
            candidate = self._mix(init, sa, sb)
            if candidate not in seen:
                seen.add(candidate)
                checks += 1
                if pred(**candidate):
                    Sk1.add(candidate)
                    valid += 1
        if not checks:
            return Sk1, 0.0, seen
        else:
            return Sk1, valid/checks, seen

    def _mix(self, init, sa, sb):
        assignment = dict()
        for k,v in init.items():
            assignment[k] = v ^ ((v ^ sa[k]) | (v ^ sb[k]))
        return HashableDict(assignment)
