import pytest
from pyscheme.atoms import Symbol
from pyscheme.parse_algebra import tokenize, parse


def test_tokenize():
    tokens = list(tokenize('1 + 3'))
    assert tokens[0].value == 1

    tokens = list(tokenize('a + 3'))
    assert tokens[0].value == Symbol('a')


def test_parse():
    assert parse(tokenize('a + 3')) == [Symbol('+'), Symbol('a'), 3]
