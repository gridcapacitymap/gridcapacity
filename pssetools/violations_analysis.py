import enum
import logging
from dataclasses import dataclass

from pssetools import wrapped_funcs as wf
from pssetools.subsystem_data import (
    get_overloaded_branches_ids,
    get_overloaded_swing_buses_ids,
    get_overloaded_trafos_3w_ids,
    get_overloaded_trafos_ids,
    get_overvoltage_buses_ids,
    get_undervoltage_buses_ids,
    print_branches,
    print_buses,
    print_swing_buses,
    print_trafos,
    print_trafos_3w,
)

log = logging.getLogger(__name__)


class Violations(enum.Flag):
    NO_VIOLATIONS = 0
    NOT_CONVERGED = enum.auto()
    BUS_OVERVOLTAGE = enum.auto()
    BUS_UNDERVOLTAGE = enum.auto()
    BRANCH_LOADING = enum.auto()
    TRAFO_LOADING = enum.auto()
    SWING_BUS_LOADING = enum.auto()


@dataclass
class ViolationsLimits:
    max_bus_voltage_pu: float
    min_bus_voltage_pu: float
    max_branch_loading_pct: float
    max_trafo_loading_pct: float
    max_swing_bus_power_mw: float


def check_violations(
    max_bus_voltage_pu: float = 1.1,
    min_bus_voltage_pu: float = 0.9,
    max_branch_loading_pct: float = 100.0,
    max_trafo_loading_pct: float = 100.0,
    max_swing_bus_power_mw: float = 1000.0,
    use_full_newton_raphson: bool = False,
) -> Violations:
    if not use_full_newton_raphson:
        wf.fdns()
    else:
        wf.fnsl()
    v: Violations = Violations.NO_VIOLATIONS
    if not wf.is_solved():
        v |= Violations.NOT_CONVERGED
        log.info("Case not solved!")
        return v
    log.info(f"\nCHECKING VIOLATIONS")
    if overvoltage_buses_ids := get_overvoltage_buses_ids(max_bus_voltage_pu):
        v |= Violations.BUS_OVERVOLTAGE
        log.info(f"Overvoltage buses ({max_bus_voltage_pu=}):")
        print_buses(overvoltage_buses_ids)
    if undervoltage_buses_ids := get_undervoltage_buses_ids(min_bus_voltage_pu):
        v |= Violations.BUS_UNDERVOLTAGE
        log.info(f"Undervoltage buses ({min_bus_voltage_pu=}):")
        print_buses(undervoltage_buses_ids)
    if overloaded_branches_ids := get_overloaded_branches_ids(max_branch_loading_pct):
        v |= Violations.BRANCH_LOADING
        log.info(f"Overloaded branches ({max_branch_loading_pct=}):")
        print_branches(overloaded_branches_ids)
    if overloaded_trafos_ids := get_overloaded_trafos_ids(max_trafo_loading_pct):
        v |= Violations.TRAFO_LOADING
        log.info(f"Overloaded 2-winding transformers ({max_trafo_loading_pct=}):")
        print_trafos(overloaded_trafos_ids)
    if overloaded_trafos_3w_ids := get_overloaded_trafos_3w_ids(max_trafo_loading_pct):
        v |= Violations.TRAFO_LOADING
        log.info(f"Overloaded 3-winding transformers ({max_trafo_loading_pct=}):")
        print_trafos_3w(overloaded_trafos_3w_ids)
    if overloaded_swing_buses_ids := get_overloaded_swing_buses_ids(
        max_swing_bus_power_mw
    ):
        v |= Violations.SWING_BUS_LOADING
        log.info(f"Overloaded swing buses ({max_swing_bus_power_mw=}):")
        print_swing_buses(overloaded_swing_buses_ids)
    log.info(f"Detected violations: {v}\n")
    return v
