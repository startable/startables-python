import os
from pathlib import Path
import pytest

from startables.readers.word import import_from_word


@pytest.fixture(scope='module')
def input_dir() -> Path:
    return Path(__file__).parent / 'input'


def test_import_from_word(input_dir):
    input_docx = os.path.join(str(input_dir), 'docx', 'simple_foo.docx')
    bundle = import_from_word(input_docx)
    assert bundle
    assert len(bundle.tables) == 1

    table = bundle.tables[0]
    assert str(table.origin) == input_docx
    assert table.name == 'FooTable'
    assert 'Key' in table.col_names
    assert 'Value' in table.col_names
    assert str(table.df.iloc[0]['Value']) in 'Aaron the Aardvark'  # 'Item_A'
