# ❗⚠️❗ This project is deprecated. Please use [pdtable](https://github.com/startable/pdtable) instead ❗⚠️❗

# startables for Python

Python package with data structures and functionality to read/write files in StarTable format and contain and manipulate the information therein.

## This project

### Talk to us

For feature requests and bugs relating specifically to this Python package, please refer to this GitHub project's issue tracker.  

For issues relating to the StarTable format specification more broadly, please consult the [StarTable standard page](https://github.com/startable/startable-standard). 

### Contribute and explore

Contributions are welcome, especially if they relate to an issue that you have previously discussed or posted in the issue tracker.  

## Installation

Available on PyPI:

```
pip install startables
```

and on conda-forge:

```
conda install startables -c conda-forge
```

## Example usage

```python
import startables as st  # << recommended import idiom
import pandas as pd

# Build table manually
df = pd.DataFrame(data=[[float('nan'), 'gnu', 3], [4, 'gnat', '{{(+ x y)}}']], columns=['a', 'b', 'c'])
col_specs = {n: ColumnMetadata(Unit(u)) for n, u in zip(['a', 'b', 'c'], ['-', 'text', 'm'])}
table_x = st.Table(df=df, name='some_table', col_specs=col_specs, destinations={'success', 'glory'})

# Accessing Table contents: use Bundle.df pandas.DataFrame interface
print(table_x.df['b'])

# Read bundle of tables from file
b = st.read_csv('animal_farm_startable_file.csv')

# Make new bundle containing a subset of this bundle's tables by name and/ or destination
farm_bundle = b.filter(name_pattern='farm')  

# Accessing tables in bundle: use Bundle.tables List interface
for t in b.tables:
    print(t.name)
# Add tables to bundle
b.tables.append(table_x)

# Remove tables from bundle by name and/or destination
removed_tables = b.pop_tables(destination='my_farm')  # tables now removed from b
    
# ... More examples to come ...

```



## Object model

### Table

`Table` contains a single StarTable table block, including table name, destination field, and equal-length columns, with each column containing a list of values and having a name and metadata (currently, a unit field and a (not-fully-implemented) remark, both of them strings). 

Table contents are stored in a pandas DataFrame. `Table.df` grants the user read/write access to this DataFrame. Table column names are stored as the DataFrame column (Series) names. Column units are stored separately. 

The user can modify the DataFrame at will using the pandas.DataFrame API, or even replace the DataFrame entirely. However, introducing columns with names not covered in the Table's column specification will break the Table. Other than that, removing columns, adding/removing rows, editing cells etc. are all fine and shouldn't break anything. 

### Bundle
`Bundle` is a container for one or more `Table`  that belong together, usually because they:
- have a common origin e.g. come from the same file or file structure, and/or
- are understood as having a common context, in particular when evaluating expressions

`Bundle` is intended as the primary interface for file I/O. The `read_csv()` and `read_excel()` functions read StarTable files in CSV and Excel format, respectively, and both return a `Bundle`, while `Bundle.to_csv()` and `Bundle.to_excel()` writes a collection of tables to these same file formats. 

### Other classes
`TableOrigin` contains an indication of where a given `Table` came from, intended for use in traceability. Currently it is just a stub that contains a single string. 

`ColumnMetadata` is a container class for a column's unit (and free-text remark, though this is not tied with read/write methods yet, so of limited utility). A Table's columns are specified by supplying a dict of column_name:ColumnMetadata that covers (at least) all column names present in the Table's child DataFrame.  

## Expressions

Table cells are allowed to contain not only literal values, but also Lisp expressions. 

`Table.evaluate_expressions(context)` will return a `Table` with expressions (if there are any) evaluated based on the given context. Can also specify `inplace=True` to do this in-place. 

`Bundle.evaluate_expressions(context)` does the same thing, but for all its child tables. 

## Unit conversion

The units of a `Table` can be converted according to a `UnitPolicy`. 

A `UnitConversion` defines how a given source unit is converted to an associated reference unit. 

```python
km_m = ScaleUnitConversion(src_unit=Unit('km'), ref_unit=Unit('m'), ref_per_src=1000)
km_m.to_ref(42)  # returns 42000
km_m.from_ref(2000)  # returns 2
```

A `UnitPolicy` contains an arbitrary number of `UnitConversion`, with the restriction that any source unit is associated to one and only one reference unit, i.e. can't include a `UnitConversion` from `'mile'` to `'km'` and another from `'mile'` to `'m'` (but sure can include one from `'km'` to `'m'` and another from `'mile'` to `'m'`). Reference units themselves are automatically added as source units, with themselves as their own reference unit through an `IdentityUnitConversion`. Conversion is then possible between any two source units that share the same reference unit. 

```python
C_K = LinearUnitConversion(Unit('°C'), Unit('K'), slope=1, intercept=273.15)
cup = CustomUnitPolicy([
    ScaleUnitConversion(Unit('km'), Unit('m'), 1000),
    ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001),
    IdentityUnitConversion(Unit('metre'), Unit('m')),   # alias of a reference unit
    C_K, 
    C_K.alias(src_unit_alias=Unit('deg_C'))  # alias of a source unit
    ])

cup.convert(42, from_unit=Unit('m'), to_unit=Unit('mm'))  # returns 42000
cup.convert(42, from_unit=Unit('mm'), to_unit=Unit('metre'))  # returns 0.042
cup.convert(42, from_unit=Unit('km'), to_unit=Unit('mm'))  # returns 42000000
cup.convert_to_ref(20, src_unit=Unit('deg_C'))  # returns 293.15
cup.ref_unit(src_unit=Unit('°C'))  # returns Unit('K')
```

A `Table`'s units are converted column by column in accordance with the `UnitPolicy`. 

- `Table.convert_to_ref_units()` converts each column to its `UnitPolicy` reference unit by calling `UnitPolicy.convert_to_ref()`
- `Table.convert_units()` converts to new units explicitly specified for each column.

- `Table.convert_to_home_units()` is a special case of `Table.convert_units()` which converts back to the Table's "home units". "Home units" are saved in the Table's col_specs and are the column units with which the `Table` was created (whether manually or read from file), unless they are explicitly changed later. 

Unit conversion does not support expressions. Expressions must be evaluated prior to unit conversion. 

## Changelog

This project was migrated to GitHub from a private server at v0.8.0. Changes prior to this are not included in the GitHub repo; nevertheless, the pre-0.8.0 changelog is documented here. *PS-##* below refers to issue numbers on a legacy YouTrack issue tracker on a private server. These issue numbers are left as is for the historical record. 

This project follows [semantic versioning](https://semver.org/). This changelog follows the guidelines published on [keepachangelog.com](https://keepachangelog.com/en/1.0.0/).

### Unreleased

In a coming release, the following items are lined up to be...

#### Added

* {...crickets chirping...}


### 0.8.5 - 2020-17-12

#### Fixed

* `pandas.read_excel()` is now called with `engine='openpyxl'` to ensure compalibility with `.xlsx` files

### 0.8.4 - 2019-12-05

#### Fixed

* `Bundle.to_csv()` puts a separator on the blank line between the header and the remainder of the file, to facilitate round-trip read using `read_csv()`. This is a quick-fix workaround, because the real problem lies with the `read_csv()` parser.

### 0.8.3 - 2019-10-30

#### Added

* [#2](https://github.com/startable/startables-python/issues/2): `read_bulk()` convenience function to read multiple StarTable files at once into a single `Bundle`. 
* `import_from_word()` utility function to parse table blocks from tables in Microsoft Word `*.docx` files. 

### 0.8.2 - 2019-10-30

#### Added

* [#5](https://github.com/startable/startables-python/issues/5): `ColumnMetadata` optional property `format_str`: format string specifying how the column's values will be formatted when writing to file using  `Bundle.to_csv()` and `Bundle.to_excel()`.
* [#6](https://github.com/startable/startables-python/issues/6): Optional `header` parameter to `Bundle.to_csv()` and `Bundle.to_excel()` to allow writing a free-text header at the top of the created file. Additionally, optional `header_sep` argument to `Bundle.to_excel()`, indicating a separator to split the header across multiple columns. 

### 0.8.1 - 2019-09-05

#### Added

* Updated setup.py and setup.cfd to enable proper release on PyPI.

### 0.8.0 - 2019-09-03

#### Changed

* First parameter of `read_csv()` renamed from `stream` to `filepath_or_buffer`. The name `stream` was inconsistent with the expected type since 0.7.3, namely `str` or `pathlib.Path` (in addition to `TextIO` streams). Also, the new name  `filepath_or_buffer` is consistent with `pandas.read_csv()`. This change will break code that has used `stream` as a named argument, though we are hopeful that this has rarely if ever been done by users of this API. 
* Removed restriction on `openpyxl` version (was previously restricted to < 2.6). This is a less crappy fix to [PS-49](https://youtrackncc/issue/PS-49) than had previously been implemented. 

#### Fixed

* [PS-52](https://youtrackncc/issue/PS-52) read_csv() throws warning when given a stream as input; asks for a filename         
* [PS-53](https://youtrackncc/issue/PS-53) Bundle.to_csv() fails when column names are not strings

### 0.7.3 - 2019-02-27

#### Fixed 

- `openpyxl<26` dependency in environment.yml
- [PS-19](https://youtrackncc/issue/PS-19) Reading from CSV can fail if not enough column delimiters on first line of CSV file
- [PS-48](https://youtrackncc/issue/PS-48) Increase compatibility of startables python library by allowing non-standard formatted .csv files
- [PS-50](https://youtrackncc/issue/PS-50) CSV files exported from Excel results in first table not being read due to UTF-8-BOM

### 0.7.2 - 2019-02-18

#### Fixed

Version [2.6.0](https://openpyxl.readthedocs.io/en/stable/changes.html#id1) of our `openpyxl` dependency, released a couple of weeks ago, contains major breaking changes (which kind of goes against the spirit of minor version updates in semantic versioning...) and these breaking changes do indeed break `startables`. To remedy this, the `openpyxl` version number is now fixed to `<2.6` in the `startables` conda package recipe. 

### 0.7.1 - 2018-11-30

#### Changed 

- **Breaking changes** in methods `Bundle.filter()` and `Bundle.pop_tables()`: 
  - Parameter `exact_name`   renamed to `name` for consistency with the naming of destination-related parameters. 
  - Ordering of parameters in signature changed to `(name, name_pattern, destination, destination_pattern, ignore_case)`
  - [PS-43](https://youtrackncc/issue/PS-43) Name and destination filters are now case-insensitive by default. Can be made case-sensitive again by setting parameter `ignore_case=False`.

#### Added

- [PS-41](https://youtrackncc/issue/PS-41) Filtering on destinations by regular expression

### 0.7.0 - 2018-11-28

All of the changes in this version address [PS-27: Add/remove tables in Bundle](https://youtrackncc/issue/PS-27)

#### Changed

**Breaking changes** in `Bundle`:

- Method `tables` renamed to `filter`. Instead of returning a `List[Table]`, now returns a `Bundle` containing the filtered tables (i.e. a subset of the original `Bundle`).
- Property `tables` introduced (not to be confused with the former method of the same name). Returns the internal list of of tables stored in this `Bundle`. 
- All list-related operations are delegated to the list returned by the `tables` property. In particular: 
  - **Can now add `Table`s to `Bundle`** (a main driver for this major change) by invoking `List`'s `append()` and `extend()` methods on `Bundle.tables`. 
  - Magic methods `__getitem__`, `__iter__`, and `__len__` have been removed. 

#### Added

- Method `Bundle.pop_tables()` to **remove a selection of `Bundle`'s member tables**, selected by name and/or destination. Returns the removed tables. (This was the other main driver for this major change.)

### 0.6.1 - 2018-11-22

#### Changed

- [PS-2](https://youtrackncc/issue/PS-2) The ordering of destinations is now preserved. Table destinations can now be supplied as any `Iterable` (changed from `Set`) and are then stored internally as a `List`, thus preserving pre-existing order (if any). **Potentially breaking change**: A `ValueError` will be raised upon encountering any duplicates in the destinations supplied to a `Table`, either when read from file or programmatically. (Because duplicates are indeed nonsensical.) Duplicates were previously eliminated silently when read from file using `read_csv` and `read_excel`, and were not possible programmatically (pedants please refrain) as they had to be given as a `Set`.

### 0.6.0 - 2018-11-20

#### Added

- Introducing: **Unit conversion machinery** [PS-10](https://youtrackncc/issue/PS-10)
- Script that publishes this readme on windwiki
- [PS-8](https://youtrackncc/issue/PS-8) A more helpful error message on syntax error raised while parsing an expression cell, guiding the user to the offending cell

#### Changed

- [PS-35](https://youtrackncc/issue/PS-35) Python version requirement relaxed to 3.6 and above (was strictly 3.6) 

#### Removed

- [PS-33](https://youtrackncc/issue/PS-33) Logging. Now gone. Was generating too much noise in client code logs.


### 0.5.5 - 2018-09-10

#### Changed

* [PS-15](https://youtrackncc/issue/PS-15)  `read_csv()` and `read_excel()` now accepts `'nan'`, `'NaN'`, and `'NAN'` as valid no-data markers. Previously, only `'-'` was accepted. 

### **0.5.4** - 2018-09-07

#### Fixed

- [PS-28](https://youtrackncc/issue/PS-28) Numeric data in text columns doesn't get read. 

### **0.5.3** - 2018-09-07

#### Fixed

* [PS-5](https://youtrackncc/issue/PS-5)  Table blocks with zero rows are ignored by read_excel() and read_csv(). 

### **0.5.2** - 2018-09-07

#### Changed

* [PS-14](https://youtrackncc/issue/PS-14) `read_csv()` now forwards `*args` and `*kwargs` to `pandas.read_csv()`, so user can now make use of `pandas.read_csv()`'s many useful arguments, not least `decimal` to control which decimal separator is used in numerical columns (typically either `'.'` or `','`). **Breaking change**: included in this forward is the previously explicitly implemented `sep` argument, which means that the default value of `sep` has now changed from `';'` to pandas' own default, `','`. This is a breaking change, but improves consistency with pandas' API. 

### **0.5.1** - 2018-08-28

#### Changed

- Column metadata (basically, just units for now) now stored in a separate field, rather than as monkeypatches on the child data frame's columns. The latter proved too fragile. 

#### Added

  - `Table.df` setter: user can now replace the Table's child dataframe, as long as all the columns of the new df are described in (and consistent with) the Table's column specification (dict of name:ColumnMetadata). If not, error is raised. 
  - [PS-4](https://youtrackncc/issue/PS-4) Ability to get `Bundle.tables()` by destination
  - [PS-13](https://youtrackncc/issue/PS-13) Add exact_name option to `Bundle.tables()`
  - Column metadata now supports not only a unit, but also a free-text remark, but this is not yet used in the file readers and writers; until it is, this feature won't be very useful. 

#### Fixed

- [PS-7](https://youtrackncc/issue/PS-7) After using `read_excel()`, `evaluate_expressions()` fails unless DataFrame index is manually reset
- Other minor bug fixes.

### **0.5.0** - 2018-08-10

Complete redesign compared to the earlier 0.1 package. Total breaking change in the API. Pandas dataframes now lie at the heart of Table objects.
Requires Python 3.6. 


