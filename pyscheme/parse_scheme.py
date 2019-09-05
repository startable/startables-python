import itertools
import io
try:
    # Accessing collections abstract classes from collections
    # has been deprecated since Python 3.3
    # Fixing as in numpy:
    # https://github.com/numpy/numpy/pull/10743/commits/53b358ce7eddf78ac2bc22045fbe25e91e663b9a
    import collections.abc as collections_abc
except ImportError:
    # For backward compatibility. Should be removed at some point.
    import collections as collections_abc

from pyscheme.atoms import atom
from pyscheme.typing import *

Token = typing.NewType('Token', str)


class LookaheadIterator(collections_abc.Iterator):
    """
    See https://stackoverflow.com/questions/1517862/using-lookahead-with-generators
    """

    def __init__(self, it):
        self.it, self.nextit = itertools.tee(iter(it))
        self._advance()

    def _advance(self):
        self.lookahead = next(self.nextit, None)

    def __next__(self):
        self._advance()
        return next(self.it)


def tokenize(code: str) -> typing.Generator[Token, None, None]:
    """Convert a string of characters into a list of tokens."""
    yield from tokenize_file(io.StringIO(code))


def tokenize_file(file: typing.Union[typing.TextIO, io.StringIO]) -> typing.Generator[Token, None, None]:
    """Generate tokens from a file"""
    for line in file:
        yield from line.replace('(', ' ( ').replace(')', ' ) ').split()


def parse(tokens: typing.Iterator[Token]) -> Expression:
    """Read first expression from a sequence of tokens."""

    def parse_internal(ts):
        t = next(ts, None)
        if t is None:
            raise SyntaxError('unexpected EOF')
        if t == '(':
            result = []
            while ts.lookahead != ')':
                result.append(parse_internal(ts))
            next(ts)  # pop the )
            return result
        elif t == ')':
            raise SyntaxError('unexpected )')
        else:
            return atom(t)

    return parse_internal(LookaheadIterator(tokens))


def parse_expression(s: str) -> Expression:
    return parse(tokenize(s))
