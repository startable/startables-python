import pytest
from pyscheme.core import Environment, evaluate
from pyscheme.atoms import Symbol


def test_eval():
    env = Environment(values=[('a', 3)])
    assert evaluate(Symbol('a'), env) == 3
    assert evaluate([Symbol('if'), True, 1, 2], env) == 1


def test_definitions():
    env = Environment(definitions=[('a', [Symbol('if'), Symbol('s'), 1, 2])])
    env.define('s', True)
    assert env.evaluate(Symbol('a')) == 1


def test_lambda():
    env = Environment()
    # ((lambda (a) (if a 1 2)) 0)
    assert env.evaluate([[Symbol('lambda'), [Symbol('a')], [Symbol('if'), Symbol('a'), 1, 2]], 0]) == 2

# @pytest.fixture
# def context():
