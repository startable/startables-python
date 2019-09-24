"""
Read starTables from CSV

Central idea is that the reader emits a stream of StarBlock objects.
This allows early abort of reads as well as generic postprocessing (
as discussed in store-module docstring).

Not implemented:
Current implementation ignores everything except table blocks.
"""
import itertools
from os import PathLike
from typing import List, Iterable, Optional, Tuple, Any
import pandas as pd
import numpy as np

from .. import pdtable
from ..store import StarBlockType, TableBundle


_TF_values = {'0': False, '1': True}
def _parse_onoff_column(values):
    try:
        as_bool = [_TF_values[v.strip()] for v in values]
    except KeyError:
        raise ValueError('Entries in onoff columns must be 0 (False) or 1 (True)')
    return np.array(as_bool, dtype=np.bool)


def _parse_float_column(values):
    return np.array(values, dtype=np.float)


_column_dtypes = {
    'text': lambda values: np.array(values, dtype=np.str),
    'onoff': _parse_onoff_column
}


def make_table(lines: List[str], sep: str, origin: Optional[pdtable.TableOriginCSV]=None) -> pdtable.Table:
    table_name = lines[0].split(sep)[0][2:]
    destinations = {s.strip() for s in lines[1].split(sep)[0].split(' ,;')}
    column_names = list(itertools.takewhile(lambda s: len(s.strip()) > 0, lines[2].split(sep)))
    n_col = len(column_names)
    units = lines[3].split(sep)[:n_col]

    column_data = [l.split(';')[:n_col] for l in lines[4:]]
    column_dtype = [_column_dtypes.get(u, _parse_float_column) for u in units]

    # build dictionary of columns iteratively to allow meaningful error messages
    columns = dict()
    for name, dtype, unit, values in zip(column_names, column_dtype, units, zip(*column_data)):
        try:
            columns[name] = dtype(values)
        except ValueError as e:
            raise ValueError(f'Unable to parse value in column {name} of table {table_name} as {unit}') from e

    return pdtable.Table(pdtable.make_pdtable(
        pd.DataFrame(columns),
        units=units,
        metadata=pdtable.TableMetadata(
            name=table_name, destinations=destinations, origin=origin)))


_token_factory_lookup = {
    StarBlockType.TABLE: make_table
}


def make_token(token_type, lines, sep, origin) -> Tuple[StarBlockType, Any]:
    factory = _token_factory_lookup.get(token_type, None)
    return token_type,  None if factory is None else factory(lines, sep, origin)


def read_file_csv(file: PathLike, sep: str = ';') -> Iterable[Optional[Tuple[StarBlockType, Any]]]:
    """
    Read starTable tokens from CSV file, yielding them one token at a time.
    """

    # Loop seems clunky with repeated init and emit clauses -- could probably be cleaned up
    # but I haven't seen how.
    lines = []
    block = StarBlockType.METADATA
    block_line = 0
    with open(file) as f:
        for line_number_0based, line in enumerate(f):
            next_block = None
            if line.startswith('**'):
                if line.startswith('***'):
                    next_block = StarBlockType.DIRECTIVE
                else:
                    next_block = StarBlockType.TABLE
            elif line.startswith(':'):
                next_block = StarBlockType.TEMPLATE_ROW
            elif line.startswith(sep) and not block == StarBlockType.METADATA:
                next_block = StarBlockType.BLANK

            if next_block is not None:
                yield make_token(block, lines, sep, pdtable.TableOriginCSV(str(file), block_line))
                lines = []
                block = next_block
                block_line = line_number_0based+1

            lines.append(line)

    if lines:
        yield make_token(block, lines, sep, pdtable.TableOriginCSV(str(file), block_line))


def read_bundle_from_csv(input_path: PathLike, sep: Optional[str] = ';') -> TableBundle:
    """Read single csv-file to TableBundle"""
    return TableBundle(read_file_csv(input_path, sep))
