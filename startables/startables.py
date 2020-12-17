"""
Pandas dataframe-based Table class with support for parametrization.
"""
import codecs
import copy
import functools
import pathlib
import re
import sys
from builtins import NotImplementedError
from io import StringIO, TextIOBase
from typing import (Dict, Generator, Iterable, List, NewType, Optional,
                    TextIO, Union)

import numpy as np
import openpyxl
import pandas as pd
from openpyxl.utils.dataframe import dataframe_to_rows

try:
    from openpyxl.worksheet.worksheet import Worksheet
except ImportError:
    # openpyxl < 2.6
    from openpyxl.worksheet import Worksheet

import pyscheme
from startables.units import Unit, UnitPolicy

nan = float('nan')

EvaluationContext = NewType('EvaluationContext', dict)
Symbol = NewType('Symbol', str)

DEFAULT_DESTINATION = 'all'
DEFAULT_UNIT_STR = 'text'
TEXT_COL_UNIT_STR = 'text'
NO_DATA_MARKERS_ON_READ = ['-', 'nan', 'NaN', 'NAN']
NO_DATA_MARKER_ON_WRITE = '-'
EXPRESSION_RE = re.compile(r'^{{.*}}$')
WHITESPACE_RE = re.compile(r'\s')


class TableOrigin:
    """
    Describes the origin of a table.
    Extend to filetype-specific classes with edit as strategy?
    """

    # TODO Excel origin should include sheet name
    # TODO how do we get document/data source? e.g. pondus/doreco, revision number etc.

    def __init__(self, text_representation: str):
        self._text_representation = text_representation

    def __str__(self) -> str:
        return self._text_representation

    def open_edit(self) -> None:
        raise NotImplementedError(
            'Functionality to open editor for "{}" not implemented'.format(str(self)))

    def get_local_file(self) -> pathlib.Path:
        raise NotImplementedError(
            'Functionality to open editor for "{}" not implemented'.format(str(self)))

    # @property
    # def text_representation(self) -> str:
    # TODO no point in having this if have __str__? (unless to be analogous to html_representation?)
    #     return self._text_representation

    # @property
    # def html_representation(self, span_class='table_origin') -> str:
    #     # TODO What's the intended use of this?
    #     return '<span class="{}">{}</span>'.format(span_class, str(self))


class ColumnMetadata:
    def __init__(self, unit: Unit, home_unit: Optional[Unit] = None, remark: Optional[str] = None,
                 format_str=None):
        """
        Metadata about the column.
        :param unit: Column unit as per https://github.com/startable/startable-standard/blob/master/StarTable%20format%20specification.md#unit
        :param home_unit: Other unit to which to convert this column upon request
        :param remark: Free-text remark about this column
        :param format_str: The format string to be applied to the data in the column when writing
         to file (Excel, CSV). Format string syntax is as described in:
         (https://docs.python.org/3.1/library/string.html#format-specification-mini-language)
         Can be supplied as either
         * a format specifier e.g. '.2f' to format 4000.04334 as '4000.04'; or
         * a full format string, composed of a format specifier wrapped between '{:' and '}' and
          optionally other characters outside the curly braces
          e.g. '${:,.2f}' to format 4000.04334 as '$4,000.04'.
        """
        # TODO better name than "home_unit"... "report_unit"? "cache_unit"?
        # JAWES had put forth "display_unit" but to JEACO this suggests the Table would be displayed with these units... which it isn't unless it's first explicitly converted to these units
        self.unit = unit
        self.home_unit = home_unit if home_unit else unit
        self.remark = remark
        if format_str:
            if '{' not in format_str and '}' not in format_str:
                format_str = '{:' + format_str + '}'
        self.format_str = format_str

    def __repr__(self):
        # TODO ensure consistency of this string with field names
        return f"{self.__class__}, unit '{self.unit}', home unit '{self.home_unit}', remark '{self.remark}', format_str '{self.format_str}'."


class ExpressionCell:

    def __init__(self, row: int, col: int, expression: pyscheme.Expression):
        self._row = row
        self._col = col
        self._expression = expression

    # @property
    # def symbols(self):
    #     return self._expression.symbols

    def update_in_data_frame(self, df: pd.DataFrame, evaluation_context: pyscheme.Environment):
        # Check that context contains all the symbols contained in this cell's expression
        df.iloc[self._row, self._col] = evaluation_context.evaluate(self._expression)


class Table:
    """
    Container for
     * a StarTable table block, with a name, destinations, and a set of columns each with a name
     and unit field and containing an equal number of cells
     * an origin, identifying where the data came from.

    Cells can contain expressions.
    When given an evaluation context, Table can return a pandas.DataFrame with evaluated expressions.

    Each column has a set of associated metadata (for now, only units).
    """

    def __init__(self, df: pd.DataFrame, name: str, col_specs: Dict[str, ColumnMetadata] = None,
                 destinations: Optional[Iterable[str]] = None, origin: Optional[TableOrigin] = None,
                 remark: Optional[str] = None):
        """

        :param df: DataFrame of Table contents.
        :param name: Name of this Table.
        :param col_specs: If supplied, specifies column metadata. If not, these are created with default values.
        :param destinations: Iterable of destination strings.
        :param origin:
        :param remark: Free-text remark about this table block.
        :param col_display_digits: If supplied, a dictionary specifying the number of digits to be rounded per given
                column name when saving to file.
        """

        if col_specs:
            self._validate_col_specs(col_specs, df.columns)
            df: pd.DataFrame = df.copy()
            self._col_specs = col_specs
        else:
            self._col_specs = {col_name: ColumnMetadata(Unit(DEFAULT_UNIT_STR)) for col_name in
                               df.columns}

        self.name = name
        if not destinations:
            destinations = [DEFAULT_DESTINATION]
        self._destinations = self._sanitize_destinations(destinations)
        self.origin = origin

        self._df = df
        self.remark = remark

    @staticmethod
    def _validate_col_specs(col_specs, df_col_names):
        missing_cols = [col_name for col_name in df_col_names if col_name not in col_specs]
        if missing_cols:
            raise ValueError(
                f'Missing column specifications for DataFrame columns: {missing_cols}.')

    def __len__(self):
        """
        Returns number of rows in table. This is consistent with pandas.DataFrame.__len__
        """
        return len(self._df)

    def __bool__(self):
        """
        We define a Table's truthiness to be True always, even when __len__==0.
        Because a Table still contains useful (meta)data, even when it has zero rows.
        """
        return True

    def __repr__(self):
        return f"{self.__class__}, name '{self.name}', destinations {self._destinations}, " \
               f"{len(self.df.columns)} columns: {self.col_names}, {len(self._df)} rows."

    @property
    def destinations(self) -> Iterable[str]:
        return self._destinations

    @destinations.setter
    def destinations(self, destinations: Iterable[str]):
        self._destinations = self._sanitize_destinations(destinations)

    @property
    def df(self) -> pd.DataFrame:
        """
        Access internal pandas.DataFrame representation of Table contents.
        Use this to:
        * read/write table cell values (including expressions)
        * add/remove rows
        * remove columns
        * add columns, if their names are covered in the column specification
        """
        return self._df

    @df.setter
    def df(self, value: pd.DataFrame):
        """
        Replace Table contents. The Table's metadata is not changed; the new DataFrame must be compatible with this.
        :param value: DataFrame whose column names are the same set as, or a subset of, those in the existing Table's column specifications.
        :return: None
        """
        self._validate_col_specs(self._col_specs, value.columns)
        self._df = value

    @property
    def col_specs(self) -> Dict[str, ColumnMetadata]:
        return self._col_specs

    @col_specs.setter
    def col_specs(self, value: Dict[str, ColumnMetadata]):
        self._validate_col_specs(value, self._df.columns)
        self._col_specs = value

    @property
    def col_names(self):
        return list(self.df.columns)

    @property
    def col_units(self):
        return [self._col_specs[col_name].unit for col_name in self._df.columns]

    def copy(self):
        # TODO Review this... clarify intent, is it shallow copy or deep copy? Does shallow copy make sense at all if metadata is shallow copied?
        return Table(self._df.copy(), name=self.name, col_specs=copy.deepcopy(self.col_specs),
                     destinations=self._destinations.copy(), origin=copy.copy(self.origin))

    def evaluate_expressions(self,
                             context: Union[Dict[str, pyscheme.Expression], pyscheme.Environment],
                             *,
                             inplace: bool = False):
        # TODO Replace context type hint with EvaluationContext defined above?
        """
        Evaluate expressions in this Table based on the given context.
        :param context: Can be a pyscheme Environment, or a dict of symbols:values
        :param inplace: If False, returns a new Table. If True, evaluates expressions in-place instead.
        """

        if isinstance(context, pyscheme.Environment):
            env = context
        else:
            env: pyscheme.Environment = pyscheme.make_root_environment()
            for k, v in context.items():
                env.define(k, v)

        expression_cells = self._find_expression_cells(self._df)

        # TODO does this validation below make sense? It isn't currently possible with pyscheme.Environment...
        # # Validate context (check that it covers all symbols in source df)
        # source_df_symbols = {s for cell in param_cells for s in cell.symbols}
        # context_symbols = set(evaluation_context.keys())
        # if not source_df_symbols.issubset(context_symbols):
        #     raise ValueError(f'Evaluation context missing some symbols present in this Table: '
        #                      f'{source_df_symbols - context_symbols}')

        if inplace:
            df = self._df
        else:
            df: pd.DataFrame = self._df.copy()

        # Evaluate
        for cell in expression_cells:
            cell.update_in_data_frame(df, env)

        if not inplace:
            t = Table(df=df, name=self.name, col_specs=self.col_specs,
                      destinations=self.destinations,
                      origin=self.origin)
            return t

    def convert_units(self, unit_policy: UnitPolicy, new_units: Dict[str, Unit] = None,
                      inplace: bool = False,
                      new_unit_missing: str = 'raise') -> Optional['Table']:
        """
        Changes values and units in accordance with unit policy.
        :param unit_policy: Unit policy that will govern unit conversion.
        :param new_units: dict of column name --> new unit. If none, unit_policy decides.
        :param inplace: If True, convert values and unit fields in-place. If False, return a new converted Table.
        :param new_unit_missing: {'ignore', 'raise'}, default 'raise'. Defines behaviour if a column's new unit is not supported
        by the unit policy. If 'raise', raise an exception. If 'ignore', leave the unit in place, no conversion done.
        # TODO what about if old unit is not in policy...
        """

        new_unit_missing_options = {'ignore', 'raise'}
        if new_unit_missing not in new_unit_missing_options:
            raise ValueError(
                f"Expected one of {new_unit_missing_options}, got '{new_unit_missing}'.")

        table = self if inplace else self.copy()

        for col in table.df:
            old_unit = self._col_specs[col].unit
            if old_unit != Unit(TEXT_COL_UNIT_STR):
                try:
                    new_unit = new_units[col]
                except KeyError:
                    if new_unit_missing == 'raise':
                        raise ValueError(f"New unit missing for column '{col}'.")
                    continue  # Move on to next column.
                try:
                    # Convert values in this col
                    table.df[col] = table.df[col].apply(unit_policy.convert, from_unit=old_unit,
                                                        to_unit=new_unit)
                    # Change this col's unit to ref_unit
                    table._col_specs[col].unit = new_unit
                except ValueError as ve:
                    raise ValueError(
                        f"Can't convert unit of column '{col}' from '{old_unit}' to '{new_unit}'.") from ve

        if not inplace:
            return table

    def convert_to_home_units(self, unit_policy: UnitPolicy, *args, **kwargs) -> Optional['Table']:
        """
        Convenience method that calls convert_units with new_units = home units
        """
        new_units = {col: self.col_specs[col].home_unit for col in self.col_names}
        return self.convert_units(unit_policy=unit_policy, new_units=new_units, *args, **kwargs)

    def convert_to_ref_units(self, unit_policy: UnitPolicy, inplace: bool = False,
                             units_not_in_policy: str = 'raise') -> Optional['Table']:
        """
        Converts values and units to unit policy's reference units.
        :param unit_policy:
        :param inplace:
        :param units_not_in_policy: {'ignore', 'raise'}, default 'raise'. Defines behaviour if a column's unit is not supported by
        the unit policy. If 'raise', raise an exception. If 'ignore', leave the unit in place, no conversion done.
        """
        # TODO unit conversion will fail on expressions

        units_not_in_policy_options = {'ignore', 'raise'}
        if units_not_in_policy not in units_not_in_policy_options:
            raise ValueError(
                f"Expected one of {units_not_in_policy_options}, got '{units_not_in_policy}'.")

        table = self if inplace else self.copy()

        for col in table.df:
            old_unit = self._col_specs[col].unit
            if not old_unit == Unit(TEXT_COL_UNIT_STR):
                try:
                    # Convert values in this col
                    table.df[col] = table.df[col].apply(unit_policy.convert_to_ref,
                                                        src_unit=old_unit)
                    # Change this col's unit to ref_unit
                    table._col_specs[col].unit = unit_policy.ref_unit(old_unit)
                except ValueError:
                    if units_not_in_policy == 'raise':
                        raise ValueError(
                            f"Unit '{old_unit}' of column '{col}' not found in unit policy.")
                    pass  # Ignore the unknown unit, do no conversion

        if not inplace:
            return table

    def to_csv(self, stream: TextIO, sep: str = ';', num_cols: Optional[int] = None) -> None:
        """
        Write this Table to stream in CSV format.
        :param stream: Output stream, usually something returned by open()
        :param sep: CSV column separator character
        :param num_cols: Number of columns to write in first CSV line, to be kind to CSV readers
                         that can't figure out how many columns there are in the tables otherwise.
                         Defaults to number of columns in Table.
        """
        self._validate_col_specs(self._col_specs, self._df.columns)
        df = self._prepare_df_for_write()
        stream.write(f'**{self.name}')
        stream.write(f'{sep * ((num_cols if num_cols else len(df.columns)) - 1)}\n')

        stream.write(' '.join(str(x) for x in self.destinations) + '\n')
        stream.write(sep.join(str(x) for x in self.col_names) + '\n')
        stream.write(sep.join(str(x) for x in self.col_units) + '\n')
        for row in df.itertuples(index=False, name=None):
            stream.write(sep.join(map(str, row)) + '\n')
        stream.write('\n')

    def to_excel(self, ws: Worksheet) -> None:
        self._validate_col_specs(self._col_specs, self._df.columns)
        ws.append([f'**{self.name}'])
        ws.append([" ".join(str(x) for x in self.destinations)])
        ws.append(self.col_names)
        ws.append(self.col_units)
        df = self._prepare_df_for_write()
        for row in dataframe_to_rows(df, index=False, header=False):
            ws.append(row)

    def _prepare_df_for_write(self) -> pd.DataFrame:
        df = self.df.fillna(NO_DATA_MARKER_ON_WRITE)
        for col, col_spec in self._col_specs.items():
            if col_spec.format_str:
                df[col] = df[col].apply(
                    lambda x: x if x == NO_DATA_MARKER_ON_WRITE else col_spec.format_str.format(x))
        return df

    def _sanitize_destinations(self, destinations: Iterable[str]) -> List[str]:
        sanitized_destinations = [str(d).strip() for d in destinations]
        for d in sanitized_destinations:
            if WHITESPACE_RE.search(d):
                raise ValueError(
                    f"Destination '{d}' contains illegal whitespace in Table '{self.name}'.")
        if len(set(sanitized_destinations)) != len(sanitized_destinations):
            raise ValueError(f"Illegal duplicate destinations in Table '{self.name}'.")
        return sanitized_destinations

    def _find_expression_cells(self, df: pd.DataFrame) -> List[ExpressionCell]:
        """
        Extracts expression cells from DataFrame
        """
        ec = []
        for col, series_name in enumerate(df):
            ser = df[series_name]
            # TODO Performance: skip Series whose dtype can't possibly contain an expression, e.g. float etc.
            # TODO ... and then remove na kwarg from ser.index[ser.str.match(EXPRESSION_PATTERN)] below since match returns boolean Series for string inputs (but NaNs otherwise, which was a slight wtf for me):
            try:
                rows_with_expr = ser.index[ser.str.match(EXPRESSION_RE, na=False)].tolist()
            except AttributeError:
                # There weren't any str in that Series. Couldn't search for expressions. Move on.
                continue
            # TODO validate expressions? syntax, maybe obvious eval error (div by zero?)
            for row in rows_with_expr:
                try:
                    expression = pyscheme.parse_expression(
                        _strip_expression_markers(df.iloc[row, col]))
                except SyntaxError as se:
                    raise SyntaxError(
                        f"Syntax error in expression in table '{self.name}', column {col}, row {row}, "
                        f"origin: {self.origin}") from se
                ec.append(ExpressionCell(row, col, expression))
        return ec


class Bundle:
    """
    Container for one or more tables that belong together, usually because they:
     * have a common origin, and/or
     * are understood as having a common context, in particular when evaluating expressions.
    """

    MIN_BUNDLE_SEPARATOR = 3

    def __init__(self, tables: Iterable[Table], origin: Optional[TableOrigin] = None):
        self._tables = list(tables)
        self.origin = origin

    def __repr__(self):
        return f'{self.__class__}, contains {len(self._tables)} tables.'

    @property
    def tables(self) -> List[Table]:
        return self._tables

    def _filter_tables(self, name: Optional[str] = None, name_pattern: str = '',
                       destination: Optional[str] = None, destination_pattern: str = '',
                       ignore_case: bool = True) -> List[Table]:
        if name_pattern and name:
            raise ValueError(
                "Both name and name_pattern were specified. Either may be specified, but not both.")
        if destination_pattern and destination:
            raise ValueError(
                "Both destination and destination_pattern were specified. Either may be specified, but not both.")
        if name is not None:
            name_pattern = '^' + re.escape(name) + '$'
        if destination is not None:
            destination_pattern = '^' + re.escape(destination) + '$'
        birthday = re.IGNORECASE if ignore_case else 0
        return [t for t in self._tables if re.search(name_pattern, t.name, flags=birthday)
                and any(re.search(destination_pattern, d, flags=birthday) for d in t.destinations)]

    def filter(self, name: Optional[str] = None, name_pattern: str = '',
               destination: Optional[str] = None, destination_pattern: str = '',
               ignore_case: bool = True) -> 'Bundle':
        """
        Returns a Bundle containing a subset of this Bundle's member tables,
        filtered by name and/or destination.
        Name and destination filters can be specified as exact strings, or as regular expression strings.
        If no name or destination filter is specified, returns a Bundle with all tables.
        :param name: An exact string for which to search table names.
        :param name_pattern: A regular expression pattern for which to search table names.
        May only be specified if name is not given.
        :param destination: A destination string required in a given table's destinations list.
        :param destination_pattern: A regular expression for which at least one match is required in a given table's
        destinations list. May only be specified if destination is not given.
        :param ignore_case: If True, will match names and destinations in a case-insensitive way. (default=True)
        """
        return Bundle(
            self._filter_tables(name, name_pattern, destination, destination_pattern, ignore_case),
            self.origin)

    def pop_tables(self, name: Optional[str] = None, name_pattern: str = '',
                   destination: Optional[str] = None, destination_pattern: str = '',
                   ignore_case: bool = True) -> List[Table]:
        """
        Removes member tables, selected by name and/or destination. Returns the removed tables.
        Name and destination filters can be specified as exact strings, or as regular expression strings.
        If no name or destination filter is specified, removes (and returns) all tables.
        :param name: An exact string for which to search table names.
        :param name_pattern: A regular expression for which to search table names.
        May only be specified if name is not given.
        :param destination: A destination string required in a given table's destinations list.
        :param destination_pattern: A regular expression for which at least one match is required in a given table's
        destinations list. May only be specified if destination is not given.
        :param ignore_case: If True, will match names and destinations in a case-insensitive way. (default=True)
        """
        tables_to_pop = self._filter_tables(name, name_pattern, destination, destination_pattern,
                                            ignore_case)
        self._tables = [t for t in self._tables if t not in tables_to_pop]
        return tables_to_pop

    def copy(self):
        return Bundle([t.copy() for t in self._tables], self.origin)

    def evaluate_expressions(self,
                             context: Union[Dict[str, pyscheme.Expression], pyscheme.Environment],
                             inplace: bool = False):
        """
        If inplace = False, returns a new Bundle with any expressions in member tables evaluated in the given context.
        If inplace = True, evaluates expressions in-place in member tables instead.
        """
        # TODO write test
        if inplace:
            for t in self._tables:
                t.evaluate_expressions(context, inplace=inplace)
        else:
            tables = [t.evaluate_expressions(context, inplace=inplace) for t in self._tables]
            for new_table, old_table in zip(tables, self._tables):
                new_table.origin = old_table.origin
            return Bundle(tables, self.origin)

    def to_csv(self, stream: TextIO, sep: str = ';', header: str = '') -> None:
        """
        :param stream:
        :param sep: column separator (i.e. delimiter) character
        :param header: text to be printed at the beginning of the csv file. If formatted as csv, will span columns and rows.
        """
        max_num_cols = max(len(t.col_names) for t in self._tables)
        if header:
            stream.write(header.rstrip())
            stream.write('\n')
            stream.write(sep * Bundle.MIN_BUNDLE_SEPARATOR)
            stream.write('\n')

        for t in self._tables:
            t.to_csv(stream, sep=sep, num_cols=max_num_cols)

    def to_excel(self, path, header: str = '', header_sep: str = ';') -> None:
        '''
        :param path: Path to the location to save excel file to.
        :param header: Text to be shown before the bundle of tables. If the text contains a newline (\n) and/or the
                header_sep, the text will span over multiple rows and/or columns, respectively, in the excel
                sheet.  Header will have one line of separation to the bundle tables.
        :param header_sep: Separator to control header text to be split onto multiple columns
        '''
        wb = openpyxl.Workbook()
        ws = wb.active

        if header:
            for row in header.rstrip().split('\n'):
                ws.append(row.split(header_sep))
            ws.append([])

        for t in self._tables:
            t.to_excel(ws)
            ws.append([])  # blank line after table block
        wb.save(path)


def read_csv(filepath_or_buffer: Union[str, pathlib.Path, TextIO], sep: str = ';', header=None,
             missing_separators: str = 'ignore', *args, **kwargs) -> Bundle:
    """Reads csv file and parses the startables

    The read is split into 3 layers:
        1. low-level reading of lines as strings
        2. pandas.read_csv()
        3. startables parsing of pandas DataFrame

    Only in the event that layer 2 parse fails, layer 1 parsing is carried out.
    Toggle layer 1 parsing & correction with arg missing_separators='ignore', if False the ParserError is re-thrown.

    Arguments:
        stream {TextIO} -- The .csv file to be parsed

    Keyword Arguments:
        sep {str} -- csv file separator character (default: {';'})
        header {[type]} -- [description] (default: {None})
        missing_separators {'ignore','raise'} -- determines behaviour when csv is missing separators.
                                                 'ignore' means try to fix by simply adding more, this
                                                 might not always be the correct thing. 
                                                 (default: {'ignore'})

    Raises:
        pandes.errors.ParserError -- if pandas csv parsing fails

    Returns:
        Bundle -- bundle with the tables read

    """

    def _parse_csv_table_block(block: str) -> pd.DataFrame:
        """ inner method for parsing a csv table block layer 1+2 """

        try:
            # attempt layer 2 parse 
            df_block = pd.read_csv(StringIO(block), sep=sep, header=header,
                                   na_values=[''], keep_default_na=False, *args, **kwargs)
        except pd.errors.ParserError as e:

            if missing_separators == 'ignore':
                first_line = block[0:block.find('\n')]
                # suppress exception and perform layer 1 parse
                print(
                    f'WARNING: CSV table block "{first_line}" in "{filename}" could not be parsed due to: "{str(e).strip()}". Will attempt fix...')

                # find the max count of sep in this block
                lines = block.split('\n')  # i shall do this only once
                sep_counts = [line.count(sep) for line in lines]  # number of seps on each line
                max_sep = max(sep_counts)

                # zip into list of tuples with [(sep_count1, line1), (sep_count2, line2), ]
                # only add if missing sep (never remove)
                corrected_lines = [t[1] if t[0] == max_sep else f'{t[1]}{sep * (max_sep - t[0])}'
                                   for t in zip(sep_counts, lines)]
                corrected_block = '\n'.join(corrected_lines)

                # retry layer 2 parse
                try:
                    df_block = pd.read_csv(StringIO(corrected_block), sep=sep, header=header,
                                           na_values=[''], keep_default_na=False, *args, **kwargs)
                except pd.errors.ParserError as e:
                    # nope, author of csv file needs slap and roundhouse kick...  :-(
                    print(
                        f'ERROR: CSV table block "{first_line}" in "{filename}" could not be corrected, still got {str(e).strip()}')
                    raise e
            else:
                # missing_separators='raise' => re-throw
                raise e

        return df_block

    # re thingies used...
    BLOCK_SEPARATOR = re.compile(r'(\n[SEP]{MIN,})+\n'.replace('SEP', sep).replace('MIN', str(Bundle.MIN_BUNDLE_SEPARATOR)))  # escape hell if f-string
    TABLE_MARKER = re.compile(r'^\*{2}(\w*)')
    DIRECTIVE_MARKER = re.compile(r'^\*{3}(\w*)')
    TEMPLATE_MARKER = re.compile(r'^:{1,3}(\w*)')
    UTF8BOM = "ï»¿"  # handle Excel export to csv, which produces UTF-8-BOM files

    # read and split the whole csv file... heavy memory usage? could this be buffered/streamed in some way?
    if not isinstance(filepath_or_buffer, TextIOBase):
        # stream is not opened, e.g. just a Path or str
        # this is the ideal scenario, as we can open the file in binary mode and read the UTF-8-BOM as bytes
        filename = filepath_or_buffer

        # detect encoding
        encoding = sys.getdefaultencoding()
        with open(filename, 'rb') as f:
            peek = f.read(4)
            # handle UTF-8-BOM from Excel export as csv
            if peek.startswith(codecs.BOM_UTF8):
                encoding = 'utf-8-sig'

        # DEBUG print(f'encoding={encoding}')

        # close and re-open with correct encoding
        with open(filename, encoding=encoding) as f:
            csv_blocks = BLOCK_SEPARATOR.split(f.read())

    else:
        # stream is already opened, because user wrapped the method in ContextManager "with open(x) as y ... "
        filename = filepath_or_buffer.name
        print(
            f'WARNING: startables.read_csv(): Excel-generated CSV files may not be decoded correctly when stream is passed. Consider passing path of file {filename} as pathlib.Path or str to ensure correct detection of encoding.')

        csv = filepath_or_buffer.read()
        csv_blocks = BLOCK_SEPARATOR.split(csv)

        # quick n dirty check for UTF-8-BOM in first block
        if csv_blocks[0].startswith(UTF8BOM):
            csv_blocks[0] = csv_blocks[0][(len(UTF8BOM)):]  # remove marker

    # parse the csv
    csv_tables = list()
    for number, block in enumerate(csv_blocks):
        # DEBUG print('----- block {} ----\n{}'.format(number, block))

        # kinda JAWES PS-19 suggestion
        if TABLE_MARKER.match(block):
            df_block = _parse_csv_table_block(block)
            # go ahead with layer 3 parse 
            csv_tables.extend(
                _extract_unparsed_tables_from_df_entire_file(df_block, TableOrigin(filename)))
        elif DIRECTIVE_MARKER.match(block):
            pass
        elif TEMPLATE_MARKER.match(block):
            pass  # belongs to the last read table?
        else:
            pass  # we dont want it, skip it

    return Bundle(csv_tables, TableOrigin(filename))


def read_excel(path) -> Bundle:
    """ file open/close is passed on to pandas.read_excel() """
    df_entire_file = _make_single_dataframe_from_excel_workbook(path)
    return _extract_bundle_from_df_entire_file(df_entire_file, TableOrigin(str(path)))


def _strip_expression_markers(expr: str) -> str:
    return expr.strip('{}')


# ---------------------------------------------------
# ----- Ugly parsing functions below ----------------
# ---------------------------------------------------


def _make_single_dataframe_from_excel_workbook(io) -> pd.DataFrame:
    """
    Given the path to an Excel workbook, create a pandas.DataFrame by stacking all sheets in the workbook.

    :param io: anything accepted by pandas.read_excel()'s io parameter
    """
    # Produce dictionary whose values are the data frames for each sheet
    dfs_by_sheet = pd.read_excel(io, sheet_name=None, header=None, na_values=[''],
                                 keep_default_na=False, engine='openpyxl')
    # We need to append a blank row to each data frame since by specification, startables
    # are separated by empty lines
    for sheet_name, df in dfs_by_sheet.items():
        blank_row = pd.Series(None, index=df.columns)
        dfs_by_sheet[sheet_name] = df.append(blank_row, ignore_index=True)
    # We explicitly reindex as the parser uses the indices to locate the startables
    return pd.concat(dfs_by_sheet.values(), ignore_index=True)


def _extract_bundle_from_df_entire_file(df_entire_file: pd.DataFrame, origin: TableOrigin):
    tables = list(_extract_unparsed_tables_from_df_entire_file(df_entire_file, origin))
    return Bundle(tables, origin=origin)


def _extract_unparsed_tables_from_df_entire_file(df_entire_file: pd.DataFrame,
                                                 origin: TableOrigin) -> Generator[
    Table, None, None]:
    # Figure out where tables start and end
    whatsthis = df_entire_file.iloc[:, 0].str

    table_start_rows = df_entire_file.index[
        df_entire_file.iloc[:, 0].str.startswith('**', na=False)].tolist()
    table_end_rows = table_start_rows[1:] + [len(df_entire_file)]

    # Parse tables one by one
    for (row_start, row_end) in zip(table_start_rows, table_end_rows):
        df_unparsed_table = df_entire_file.iloc[row_start:row_end]
        table = _parse_table_from_unparsed_table_dataframe(df_unparsed_table, origin)
        if table:
            yield table


def _parse_table_from_unparsed_table_dataframe(df_unparsed_table: pd.DataFrame,
                                               origin: TableOrigin) -> Optional[Table]:
    """
    If given a pandas.DataFrame that contains an entire table block including name and destination fields,
    return a parsed Table.
    If DataFrame contains something else e.g. directive block, return None.
    """

    table_name = df_unparsed_table.iloc[0, 0][2:]
    if table_name.startswith('*'):
        # Directive. Not yet supported. Ignore.
        return None

    destinations = list(str(df_unparsed_table.iloc[1, 0]).strip().split())

    # TODO handle metadata lines
    # TODO handle tables without spacing
    n_rows = np.append(df_unparsed_table.iloc[4:, 0].isna().values, [True]).argmax()
    num_cols = np.nonzero(np.append(df_unparsed_table.iloc[2, :].isnull().values, [True], 0))[0][0]

    column_series = []
    col_specs = {}
    # Loop over columns
    for col in range(num_cols):
        col_name = str(df_unparsed_table.iloc[2, col]).strip()
        unit: Unit = str(df_unparsed_table.iloc[3, col])
        column: pd.Series = df_unparsed_table.iloc[4:(4 + n_rows), col]
        if unit == TEXT_COL_UNIT_STR:
            # Pandas reads empty fields as NaN. Convert to empty str
            column = column.astype(str).str.strip().replace(nan, '')
        elif unit == 'datetime':
            if any(column.isna()):
                raise ValueError(
                    f"Illegal empty cell in datetime column '{col_name}' of table '{table_name}'.")
            if any(column.apply(_is_illegal_value_in_datetime_column)):
                raise ValueError(
                    f"Illegal string in datetime column '{col_name}' of table '{table_name}'.")
            column = column.apply(func=_to_datetime, errors='ignore').replace(
                NO_DATA_MARKERS_ON_READ, nan)
        else:
            # By default, interpret as a column of numeric values
            if any(column.isna()):
                raise ValueError(
                    f"Illegal empty cell in numerical column '{col_name}' of table '{table_name}'.")
            if any(column.apply(_is_illegal_value_in_numeric_column)):
                raise ValueError(
                    f"Illegal string in numerical column '{col_name}' of table '{table_name}'.")
            column = column.apply(func=pd.to_numeric, errors='ignore').replace(
                NO_DATA_MARKERS_ON_READ, nan)

            # TODO add feature: when parsing numeric and datetime cols: errors='ignore', 'coerce', 'raise' like pd.to_numeric

        col_specs[col_name] = ColumnMetadata(unit)
        column.name = col_name  # To make sure columns are properly named in the dataframe
        column_series.append(column)
        # TODO to halve memory footprint, operate directly on df_unparsed_table, rather than create a new DataFrame

    df_new = pd.concat(column_series, axis=1)
    df_new.reset_index(inplace=True, drop=True)

    table = Table(df=df_new, name=table_name, col_specs=col_specs, destinations=destinations,
                  origin=origin)
    return table


# Preferred datetime conversion: try 'day first' (which is what Excel uses when saving CSV). Still works if year first.
_to_datetime = functools.partial(pd.to_datetime, dayfirst=True)


# TODO Not robust, Excel CSV date format probably depends on regional settings!


def _is_illegal_value_in_numeric_column(x) -> bool:
    if x in NO_DATA_MARKERS_ON_READ or _is_expression_str(x):
        return False
    return np.isnan(pd.to_numeric(x, errors='coerce'))


def _is_illegal_value_in_datetime_column(x) -> bool:
    if x in NO_DATA_MARKERS_ON_READ or _is_expression_str(x):
        return False
    return pd.isna(_to_datetime(x, errors='coerce'))


def _is_expression_str(x) -> bool:
    try:
        return bool(EXPRESSION_RE.match(x))
    except TypeError:
        return False  # It wasn't a string, so definitely not an expression string
