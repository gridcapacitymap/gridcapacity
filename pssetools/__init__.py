import logging
import os
import sys
from typing import Final

from pssetools.path_helper import get_psse35_paths

psse35_paths = get_psse35_paths()
sys.path = psse35_paths + sys.path
os.environ["PATH"] = os.pathsep.join((*psse35_paths, os.environ["PATH"]))
import psse35

# `psspy` should be imported only after importing `psse35`
import psspy
import redirect

from pssetools import wrapped_funcs as wf
from pssetools.capacity_analysis import CapacityAnalysisStats, buses_headroom
from pssetools.config import ConfigModel, load_config_model
from pssetools.output import write_output
from pssetools.violations_analysis import ViolationsLimits, ViolationsStats


def init_psse() -> None:
    try:
        redirect.py2psse()
    except redirect.RedirectError:
        pass
    psspy.psseinit()
    if not os.environ.get("PSSE_TOOLS_VERBOSE"):
        # Suppress all PSSE output
        no_output: Final[int] = 6
        wf.alert_output(no_output)
        wf.progress_output(no_output)
        wf.prompt_output(no_output)
        wf.report_output(no_output)


def build_headroom() -> None:
    logging_level: int = (
        logging.WARNING if not os.environ.get("PSSE_TOOLS_VERBOSE") else logging.DEBUG
    )
    logging.basicConfig(level=logging_level)
    init_psse()
    if len(sys.argv) != 2:
        raise RuntimeError(
            f"Config file name should be specified "
            f"as a program argument. Got {sys.argv}"
        )
    config_file_name: str = sys.argv[1]
    config_model: ConfigModel = load_config_model(config_file_name)
    headroom = buses_headroom(**config_model.dict(exclude_unset=True))
    if len(headroom):
        write_output(config_model.case_name, headroom)
        CapacityAnalysisStats.print()
        print()
        print(" HEADROOM ".center(80, "="))
        for bus_headroom in headroom:
            print(bus_headroom)
        if not ViolationsStats.is_empty():
            print()
            print(" VIOLATIONS STATS ".center(80, "="))
            ViolationsStats.print()
        else:
            print("No violations detected")
    else:
        print("No headroom found")


if __name__ == "__main__":
    build_headroom()
