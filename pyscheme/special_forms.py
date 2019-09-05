import math
import operator as op

from pyscheme.atoms import Symbol
from pyscheme.core import Environment
from pyscheme.typing import *


def make_root_environment() -> Environment:
    """
    An environment with some Scheme standard procedures and constants.
    """
    env = Environment()
    env.update(vars(math))  # sin, cos, sqrt, pi, ...  # TODO should this be [(k, v) for k, v in vars(math).items()] ??
    env.update({
        '+':          op.add,
        '-':          op.sub,
        '*':          op.mul,
        '/':          op.truediv,
        '>':          op.gt,
        '<':          op.lt,
        '>=':         op.ge,
        '<=':         op.le,
        '=':          op.eq,
        'abs':        abs,
        'round':      round,
        'mod':        op.mod,
        'expt':       op.pow,
        'cosd':       lambda x: math.cos(math.radians(x)),
        'sind':       lambda x: math.sin(math.radians(x)),
        'tand':       lambda x: math.tan(math.radians(x)),
        'acosd':      lambda x: math.degrees(math.acos(x)),
        'asind':      lambda x: math.degrees(math.asin(x)),
        'atand':      lambda x: math.degrees(math.atan(x)),
        'atan2d':     lambda y, x: math.degrees(math.atan2(y, x)),
        'append':     op.add,
        'begin':      lambda *x: x[-1],
        'car':        lambda x: x[0],
        'cdr':        lambda x: x[1:],
        'cons':       lambda x,y: [x] + y,
        'eq?':        op.is_,
        'equal?':     op.eq,
        'length':     len,
        'list':       lambda *x: list(x),
        'list?':      lambda x: isinstance(x,list),
        'map':        map,
        'max':        max,
        'min':        min,
        'not':        op.not_,
        'null?':      lambda x: x == [],
        'number?':    lambda x: isinstance(x, Number),
        'procedure?': callable,
        'symbol?':    lambda x: isinstance(x, Symbol),
    })
    # Wrap so that defines will not clear values
    return Environment(parent=env)

# TODO: add let and progn to root env, either directly or via a macro-functionality
