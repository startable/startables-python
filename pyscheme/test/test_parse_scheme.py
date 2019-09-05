import pytest
from pyscheme.atoms import Symbol
from pyscheme.parse_scheme import tokenize, parse_expression


def test_tokenize():
    tokens = list(tokenize('(+ a 3)'))
    assert tokens[0] == '('


def test_parse():
    assert parse_expression('(if 1 a (+ a 1))') == [Symbol('if'), 1, Symbol('a'), [Symbol('+'), Symbol('a'), 1]]

# @pytest.fixture
# def context():
