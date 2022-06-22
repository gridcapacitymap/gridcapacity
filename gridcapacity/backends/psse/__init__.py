import os
import sys
from typing import Final

assert sys.platform == "win32"

from .path_helper import get_psse35_paths

psse35_paths = get_psse35_paths()
sys.path = psse35_paths + sys.path
os.environ["PATH"] = os.pathsep.join((*psse35_paths, os.environ["PATH"]))

# `psspy` should be imported only after importing `psse35`
import psse35
import psspy
import redirect

from . import wrapped_funcs as wf


def init_psse() -> None:
    try:
        redirect.py2psse()
    except redirect.RedirectError:
        pass
    psspy.psseinit()
    if not os.environ.get("GRID_CAPACITY_VERBOSE"):
        # Suppress all PSSE output
        no_output: Final[int] = 6
        wf.alert_output(no_output)
        wf.progress_output(no_output)
        wf.prompt_output(no_output)
        wf.report_output(no_output)
