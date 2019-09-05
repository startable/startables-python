import pytest
from pyscheme.atoms import Symbol
from pyscheme.special_forms import make_root_environment


@pytest.fixture
def env():
    return make_root_environment()


def test_algebra(env):
    assert env.evaluate([Symbol('+'), 1, 2]) == 3
