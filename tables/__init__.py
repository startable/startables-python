from . import store
from . import pdtable

from .readers.read_csv import read_bundle_from_csv
from .pdtable import Table, TableOrigin


def get_units(df: pdtable.PandasTable):
    t = pdtable.Table(df)
    [c.name for c in t.columns]

