import os
from pathlib import Path

import pytest

from startables.readers.bulk import read_bulk


@pytest.fixture(scope='module')
def input_dir() -> Path:
    return Path(__file__).parent / 'input'


@pytest.fixture(scope='module')
def bulk_dir(input_dir) -> Path:
    return input_dir / 'read_bulk'


def test_read_bulk(bulk_dir):
    bundle = read_bulk(bulk_dir)
    assert bundle  # is not None
    assert len(bundle.tables) == 3
    assert len(bundle.filter(name_pattern='BarTable').tables) == 1
    assert len(bundle.filter(name_pattern='BazBass').tables) == 2
