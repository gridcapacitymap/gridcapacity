import errno
import os
import sys

# TODO: change to regular import after moving to Python 3
if sys.version_info[0] == 3:
    from pathlib import Path
else:
    from pathlib2 import Path

import pssepath

try:
    pssepath.add_pssepath()
except pssepath.PsseImportError:
    psse35_3_install_path = Path(r"C:\Program Files\PTI\PSSE35\35.3")
    if psse35_3_install_path.exists():
        py_major_minor_version_str = "".join(
            (str(sys.version_info[i]) for i in range(2))
        )
        for sub_dir_name in (
            "PSSPY" + py_major_minor_version_str,
            "PSSBIN",
        ):
            sub_dir_path = psse35_3_install_path / sub_dir_name
            if sub_dir_path.exists:
                sys.path.insert(0, str(sub_dir_path))
                os.environ["PATH"] = ";".join((str(sub_dir_path), os.environ["PATH"]))
            else:
                print("Not found" + str(sub_dir_path))

import psspy
import redirect


def init_psse():
    redirect.py2psse()
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
    print("Starting simulation of " + str(case_path))
    psspy.case(str(case_path))
    psspy.fdns()


if __name__ == "__main__":
    run_simulation()
