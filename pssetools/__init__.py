import errno
import os
import sys
from pathlib import Path

import pssepath

try:
    pssepath.add_pssepath()
except pssepath.PsseImportError:
    # No PSSE <35 path found
    # Add PSSE 35 path
    from pssetools.path_helper import get_psse35_paths

    psse35_paths = get_psse35_paths()
    sys.path = psse35_paths + sys.path
    os.environ["PATH"] = os.pathsep.join((*psse35_paths, os.environ["PATH"]))
    import psse35

import psspy
import redirect

from pssetools import wrapped_funcs as wf


def init_psse():
    try:
        redirect.py2psse()
    except redirect.RedirectError:
        pass
    psspy.psseinit()


def get_case_path(case_name):
    probable_case_path = Path(case_name)
    case_path = case_path = (
        probable_case_path
        if probable_case_path.is_absolute()
        else get_example_case_path(probable_case_path)
    )
    if not case_path.exists():
        raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), str(case_path))
    return case_path


def get_example_case_path(case_path):
    """Get example case filepath from the case filename.

    The `EXAMPLE` directory is retrieved based on the current `psspy` module location."""
    psspy_path = Path(psspy.__file__)
    psse_path = psspy_path.parents[1]
    examples_path = psse_path / "EXAMPLE"
    case_path = examples_path / case_path
    return case_path


def run_simulation():
    init_psse()
    case_name = sys.argv[1] if len(sys.argv) == 2 else "savnw.sav"
    case_path = get_case_path(case_name)
    print(f"Starting simulation of '{case_path}'")
    if case_path.suffix == ".sav":
        wf.case(str(case_path))
    elif case_path.suffix == ".raw":
        wf.read(0, str(case_path))
    wf.fdns()
    if not wf.is_solved():
        return
    print(f"Case solved")


if __name__ == "__main__":
    run_simulation()
