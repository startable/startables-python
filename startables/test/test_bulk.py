import os
from pathlib import Path

import pytest

from startables import read_bulk, import_from_word


@pytest.fixture(scope='module')
def input_dir() -> Path:
    return Path(__file__).parent / 'input'


@pytest.fixture(scope='module')
def bulk_dir(input_dir) -> Path:
    return input_dir / 'read_bulk'


def test_read_bulk_dir(bulk_dir):
    b = read_bulk(bulk_dir)
    assert b  # is not None
    assert len(b.tables) == 3
    assert len(b.filter(name_pattern='BarTable').tables) == 1
    assert len(b.filter(name_pattern='BazBass').tables) == 2


def test_read_bulk_glob(bulk_dir):
    b = read_bulk(str(bulk_dir / '*'))
    assert b  # is not None
    assert len(b.tables) == 3
    assert len(b.filter(name_pattern='BarTable').tables) == 1
    assert len(b.filter(name_pattern='BazBass').tables) == 2


def test_read_bulk_list_of_files(bulk_dir):
    b = read_bulk([bulk_dir / 'simple_bar.csv', bulk_dir / 'simple_baz_with2sheets.xlsx'])
    assert b  # is not None
    assert len(b.tables) == 3
    assert len(b.filter(name_pattern='BarTable').tables) == 1
    assert len(b.filter(name_pattern='BazBass').tables) == 2


def test_read_bulk_readers_include_docx(bulk_dir, input_dir):
    b = read_bulk([bulk_dir,
                   input_dir / 'docx' / 'simple_foo.docx'],
                  readers={'docx': import_from_word})
    assert len(b.tables) == 4


def test_read_bulk_readers_exclude_default(bulk_dir):
    b = read_bulk(bulk_dir, readers={'xlsx': None})
    assert len(b.tables) == 1
