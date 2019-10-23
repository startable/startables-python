import glob
import os
from pathlib import Path
from typing import Union, Iterable, List

from startables import Bundle, read_csv, read_excel


def read_bulk(path_specs: Union[str, Path, Iterable[Union[str, Path]]]) -> Bundle:
    """Reads all files from supplied paths and returns a single Bundle containing all table blocks read from all files.
       Supported extensions are: [csv, xlsx] (soon docx?)

    Arguments:
        path_specs {[type]} -- Can be a file, a folder or a glob expression that contains StarTable files with supported extensions. Can also be an Iterable of files, folders, and glob expressions.

    Returns:
        Bundle -- [description]

    NOTES:
    Multiple tables with the same name (within or across files) are preserved as such in the output
    bundle.
    Microsoft Office temp files (starting with "~$" or ending with ".tmp") are ignored when bulk
    reading a folder or glob expression.
    """

    if isinstance(path_specs, str) or isinstance(path_specs, Path):
        # Pack single path in something that's iterable, for later convenience
        path_specs = [path_specs]

    # First expand the path specs and collect the files they cover
    bulk_files = _collect_bulk_file_paths(path_specs)

    # Now read all the collected files into a single bundle
    collected_bundle = _read_bulk_files_to_bundle(bulk_files)

    return collected_bundle


def _read_bulk_files_to_bundle(bulk_files: List[str]) -> Bundle:
    """
    Read list of individual file paths into a single Bundle.
    """
    collected_bundle = Bundle(tables=[])
    for path in bulk_files:

        # switch on extensions
        ext = os.path.splitext(path)[1].lower()

        this_bundle = None
        if ext in (".csv",):
            with open(path) as csv:
                this_bundle = read_csv(csv)
        # elif ext in (".docx",):
        #     bundle = read_word(filename)
        elif ext in (".xlsx",):
            this_bundle = read_excel(path)
        else:
            pass  # Ignore file

        # read something?
        if this_bundle:
            collected_bundle = Bundle(collected_bundle.tables + this_bundle.tables)
    return collected_bundle


def _collect_bulk_file_paths(path_specs: Union[str, Path, Iterable[Union[str, Path]]]) -> List[str]:
    """
    Expand the path specs into a list of individual file paths.
    :param path_specs: Can be a file, a folder or a glob expression that contains StarTable files with supported extensions. Can also be an Iterable of files, folders, and glob expressions.
    :return: List of individual file paths covered by path_specs.
    """
    bulk_files = list()
    for path in path_specs:
        path = str(path)
        if os.path.isfile(path):
            # single file
            bulk_files.append(path)
        elif os.path.isdir(path):
            # folder
            for fn in os.listdir(path):
                if not _is_temp_garbage(fn):
                    bulk_files.append(os.path.join(path, fn))
        elif "*" in path:
            # glob expression
            for fn in glob.glob(path):
                if not _is_temp_garbage(fn):
                    bulk_files.append(os.path.join(path, fn))
        else:
            raise FileNotFoundError(path)
    return bulk_files


def _is_temp_garbage(filename: str):
    """Is this a Microsoft Office temp file?"""
    return filename.startswith("~$") or filename.endswith(".tmp")

