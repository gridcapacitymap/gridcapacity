import logging
import os
import sys
from typing import Final

from pssetools.path_helper import get_psse35_paths

log = logging.getLogger(__name__)

psse35_paths = get_psse35_paths()
sys.path = psse35_paths + sys.path
os.environ["PATH"] = os.pathsep.join((*psse35_paths, os.environ["PATH"]))
import psse35

# `psspy` should be imported only after importing `psse35`
import psspy
import redirect

from pssetools import wrapped_funcs as wf
from pssetools.capacity_analysis import buses_headroom
from pssetools.violations_analysis import ViolationsLimits


def init_psse():
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


def run_check():
    logging_level: int = (
        logging.WARNING if not os.environ.get("PSSE_TOOLS_VERBOSE") else logging.DEBUG
    )
    logging.basicConfig(level=logging_level)
    init_psse()
    case_name = sys.argv[1] if len(sys.argv) == 2 else "savnw.sav"
    wf.open_case(case_name)
    wf.fdns()
    use_full_newton_raphson: bool = False if wf.is_solved() else True
    if use_full_newton_raphson:
        # `options6=1` Flat start
        wf.fnsl(options6=1)
        if not wf.is_solved():
            log.warning(f"The base {case_name=} wasn't solved. Exiting.")
            return
    log.info(f"Case solved")

    normal_limits: ViolationsLimits = ViolationsLimits(
        max_bus_voltage_pu=1.1,
        min_bus_voltage_pu=0.9,
        max_branch_loading_pct=100.0,
        max_trafo_loading_pct=110.0,
        max_swing_bus_power_mva=1000.0,
    )
    contingency_limits: ViolationsLimits = ViolationsLimits(
        max_bus_voltage_pu=1.12,
        min_bus_voltage_pu=0.88,
        max_branch_loading_pct=120.0,
        max_trafo_loading_pct=120.0,
        max_swing_bus_power_mva=1000.0,
    )
    headroom = buses_headroom(
        upper_load_limit_p_mw=100.0,
        upper_gen_limit_p_mw=80.0,
        normal_limits=normal_limits,
        contingency_limits=contingency_limits,
        use_full_newton_raphson=use_full_newton_raphson,
    )
    print("Available additional capacity:")
    for bus_headroom in headroom:
        print(bus_headroom)


if __name__ == "__main__":
    run_check()
