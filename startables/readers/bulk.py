import glob
import os
from pathlib import Path
from typing import Union, Iterable, Set, Callable, Dict, Optional

from startables import Bundle, read_csv, read_excel

DEFAULT_READERS = {'xlsx': read_excel, 'csv': read_csv}


def read_bulk(path_specs: Union[str, Path, Iterable[Union[str, Path]]],
              readers: Dict[str, Optional[Callable]] = None) -> Bundle:
    """
    Reads all files with supported extensions from supplied path specs and returns a single Bundle
    containing all table blocks read from all files. Any given file's extension determines which
    reader is used to read that file.

    Path specs can be any mix of one or more files, directories, and/or glob expressions.

    Default extensions and corresponding readers are:
        {'xlsx': startables.read_excel,
         'csv' : startables.read_csv}.
    Use the 'readers' argument to overwrite the default extension-reader mapping. This can be used
    to:
        * add more readers for other extensions, e.g.
          readers={**DEFAULT_READERS, **{'docx': startables.import_from_word}};
        * remove the default readers to prevent the default extensions from being read; and/or
        * replace the default readers for the default extensions, e.g.
          readers={**DEFAULT_READERS, **{'csv': functools.partial(read_csv, sep=',')}}.

    Multiple tables with the same name (within or across files) are preserved as such in the output
    bundle.

    Microsoft Office temp files (starting with "~$" or ending with ".tmp") are ignored when bulk
    reading a folder or glob expression.

    :param path_specs: Can be a file, a folder or a glob expression that contains StarTable files
        with supported extensions. Can also be an Iterable of files, folders, and glob expressions.
    :param readers: Dict of form {'ext': reader_func} specifying what function to use to
     read files with extensions beyond the default ext.
     Default: {'xlsx': startables.read_excel, 'csv': startables.read_csv}.
     reader_func must be a callable that takes a single path argument and returns a Bundle.
     File with extensions whose reader is set to None will not be read, e.g. {'xlsx': None, ...}
    :return: Bundle containing the tables read from all files.
    """

    if readers is None:
        readers = DEFAULT_READERS

    if isinstance(path_specs, str) or isinstance(path_specs, Path):
        # Pack single path in something that's iterable, for later convenience
        path_specs = [path_specs]

    # First expand the path specs and collect the files they cover
    bulk_files = _collect_bulk_file_paths(path_specs)

    # Now read all the collected files into a single bundle
    collected_bundle = _read_bulk_files_to_bundle(bulk_files, readers)

    return collected_bundle


def _read_bulk_files_to_bundle(bulk_files: Iterable[str],
                               readers: Dict[str, Callable] = None) -> Bundle:
    """
    Read multiple individual file paths into a single Bundle.
    """
    collected_bundle = Bundle(tables=[])
    for path in bulk_files:
        # Switch on filename extension
        ext = os.path.splitext(path)[1].lower()[1:]  # strip splitext's leading '.'
        if ext in readers and readers[ext] is not None:
            # Throw this file's contents onto the pile
            collected_bundle = Bundle(collected_bundle.tables + readers[ext](path).tables)
        else:
            pass  # Ignore file

    return collected_bundle


def _collect_bulk_file_paths(path_specs: Union[str, Path, Iterable[Union[str, Path]]]) -> Set[str]:
    """
    Expand the path specs into a list of individual file paths.
    :return: Set of individual file paths covered by path_specs.
    """
    bulk_files = set()
    for path in path_specs:
        path = str(path)
        if os.path.isfile(path):
            # single file
            bulk_files.add(path)
        elif os.path.isdir(path):
            # folder
            for fn in os.listdir(path):
                if not _is_temp_garbage(fn):
                    bulk_files.add(os.path.join(path, fn))
        elif "*" in path:
            # glob expression
            for fn in glob.glob(path):
                if not _is_temp_garbage(fn):
                    bulk_files.add(os.path.join(path, fn))
        else:
            raise FileNotFoundError(path)
    return bulk_files


def _is_temp_garbage(filename: str):
    """Is this a Microsoft Office temp file?"""
    return filename.startswith("~$") or filename.endswith(".tmp")
