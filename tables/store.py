"""
The store module implements data structures for storing collections of tables.

Plan is to implement processing of a stream of StarBlockType tokens
in a generic way that can be reused across readers and storage backends.
Examples include:
- attach template tokens to previous table
- attach file level metadata to subsequent tables
- unit normalization
- directive handling
"""


from enum import Enum, auto
from typing import Iterable, Tuple, Any, Iterator, Optional


from . import pdtable


class StarBlockType(Enum):
    """
    An enumeration of the tokens types that may be emitted by a reader.

    Design note
    Members of this enum are used to tag token type to avoid introspection.
    To aid reusable generation of metadata, it could be relevant to include
    synthetic block types FILE_BEGIN/END, SHEET_BEGIN/END.
    """
    DIRECTIVE = auto()
    TABLE = auto()          # Interface: TableType
    TEMPLATE_ROW = auto()
    METADATA = auto()
    BLANK = auto()


TableType = pdtable.PandasTable


class TableBundle:
    """
    Simple table store with no regard for destinations

    Ignores everything but Table-tokens
    """

    def __init__(self, ts: Iterable[Optional[Tuple[StarBlockType, Any]]]):
        self._tables = {token.name: token.pdtable for token_type, token in ts
                        if token is not None and token_type == StarBlockType.TABLE}

    def __getattr__(self, name: str) -> TableType:
        return self._tables[name]

    def __getitem__(self, name: str) -> TableType:
        return self._tables[name]

    def __iter__(self) -> Iterator[str]:
        """Iterator over table names"""
        return iter(self._tables)
