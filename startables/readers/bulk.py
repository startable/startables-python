import glob
import os
from pathlib import Path
from typing import Union, Iterable

from startables import Bundle, read_csv, read_excel


def read_bulk(paths: Union[str, Path, Iterable[Union[str, Path]]]) -> Bundle:
    """Reads all files from supplied paths and returns a single Bundle containing all table blocks read from all files.
       Supported extensions are: [csv, xlsx] (soon docx?)

    Arguments:
        paths {[type]} -- Can be a file, a folder or a glob expression that contains Startables files with supported extensions. Can also be an Iterable of files, folders, and glob expressions.

    Returns:
        Bundle -- [description]

    NOTES:
    Multiple tables with the same name (within or across files) are preserved as such in the output
    bundle.
    Microsoft Office temp files (starting with "~$" or ending with ".tmp") are ignored when bulk
    reading a folder or glob expression.
    """

    if isinstance(paths, str) or isinstance(paths, Path):
        # Pack single path in something that's iterable, for later convenience
        paths = [paths]

    def is_temp_garbage(filename: str):
        """Is this a Microsoft Office temp file?"""
        return filename.startswith("~$") or filename.endswith(".tmp")

    # First collect the files
    bulk_files = list()
    for path in paths:
        path = str(path)
        if os.path.isfile(path):
            # single file
            bulk_files.append(path)
        elif os.path.isdir(path):
            # folder
            for fn in os.listdir(path):
                if not is_temp_garbage(fn):
                    bulk_files.append(os.path.join(path, fn))
        elif "*" in path:
            # glob expression
            for fn in glob.glob(path):
                if not is_temp_garbage(fn):
                    bulk_files.append(os.path.join(path, fn))
        else:
            raise FileNotFoundError(path)

    # Now read all files into a single bundle
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
