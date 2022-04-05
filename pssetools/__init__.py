import os
import sys

from pssetools.path_helper import get_psse35_paths

psse35_paths = get_psse35_paths()
sys.path = psse35_paths + sys.path
os.environ["PATH"] = os.pathsep.join((*psse35_paths, os.environ["PATH"]))
import psse35

import psspy
import redirect

from pssetools import wrapped_funcs as wf
from pssetools.analysis import check_violations


def init_psse():
    try:
        redirect.py2psse()
    except redirect.RedirectError:
        pass
    psspy.psseinit()


def run_check():
    init_psse()
    case_name = sys.argv[1] if len(sys.argv) == 2 else "savnw.sav"
    wf.open_case(case_name)
    wf.fdns()
    if not wf.is_solved():
        return
    print(f"Case solved")

    # Disable single branch. `intgar=0` is disabled, 1 - enabled.
    # psspy.branch_chng_3(153, 154, "1", intgar=0)
    check_violations()
    # wf.rate_2(0, 1, 1, 1, 1, 1, 100.0)


if __name__ == "__main__":
    run_check()
