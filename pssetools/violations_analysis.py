import enum
import logging
import os
from dataclasses import dataclass
from typing import Final, Optional

import psspy

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
from pssetools.wrapped_funcs import PsseApiCallError

log = logging.getLogger(__name__)
LOG_LEVEL: Final[int] = (
    logging.INFO
    if not os.getenv("PSSE_TOOLS_TREAT_VIOLATIONS_AS_WARNINGS")
    else logging.WARNING
)


class PowerFlows:
    _power_flows_count: int = 0

    @classmethod
    @property
    def count(cls) -> int:
        return cls._power_flows_count

    @classmethod
    def increment_count(cls) -> None:
        cls._power_flows_count += 1

    @classmethod
    def reset_count(cls) -> None:
        cls._power_flows_count = 0


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
    max_swing_bus_power_mva: float


class SolutionConvergenceIndicator(enum.IntFlag):
    MET_CONVERGENCE_TOLERANCE = 0
    ITERATION_LIMIT_EXCEEDED = 1
    BLOWN_UP = 2
    RSOL_CONVERGED_WITH_PHASE_SHIFT_LOCKED = 10
    RSOL_CONVERGED_WITH_TOLN_INCREASED = 11
    RSOL_CONVERGED_WITH_Y_LOAD_CONVERSION_DUE_TO_LOW_VOLTAGE = 12


def check_violations(
    max_bus_voltage_pu: float = 1.1,
    min_bus_voltage_pu: float = 0.9,
    max_branch_loading_pct: float = 100.0,
    max_trafo_loading_pct: float = 100.0,
    max_swing_bus_power_mva: float = 1000.0,
    use_full_newton_raphson: bool = False,
    solver_opts: Optional[dict] = {"options1": 1, "options5": 1},
) -> Violations:
    """Default solver options:
    `options1=1` Use tap adjustment option setting
    `options5=1` Use switched shunt adjustment option setting
    """
    run_solver(use_full_newton_raphson, solver_opts)
    v: Violations = Violations.NO_VIOLATIONS
    if not wf.is_solved():
        v |= Violations.NOT_CONVERGED
        log.log(LOG_LEVEL, "Case not solved!")
        return v
    log.info(f"\nCHECKING VIOLATIONS")
    if overvoltage_buses_ids := get_overvoltage_buses_ids(max_bus_voltage_pu):
        v |= Violations.BUS_OVERVOLTAGE
        log.log(LOG_LEVEL, f"Overvoltage buses ({max_bus_voltage_pu=}):")
        print_buses(overvoltage_buses_ids)
    if undervoltage_buses_ids := get_undervoltage_buses_ids(min_bus_voltage_pu):
        v |= Violations.BUS_UNDERVOLTAGE
        log.log(LOG_LEVEL, f"Undervoltage buses ({min_bus_voltage_pu=}):")
        print_buses(undervoltage_buses_ids)
    if overloaded_branches_ids := get_overloaded_branches_ids(max_branch_loading_pct):
        v |= Violations.BRANCH_LOADING
        log.log(LOG_LEVEL, f"Overloaded branches ({max_branch_loading_pct=}):")
        print_branches(overloaded_branches_ids)
    if overloaded_trafos_ids := get_overloaded_trafos_ids(max_trafo_loading_pct):
        v |= Violations.TRAFO_LOADING
        log.log(
            LOG_LEVEL, f"Overloaded 2-winding transformers ({max_trafo_loading_pct=}):"
        )
        print_trafos(overloaded_trafos_ids)
    if overloaded_trafos_3w_ids := get_overloaded_trafos_3w_ids(max_trafo_loading_pct):
        v |= Violations.TRAFO_LOADING
        log.log(
            LOG_LEVEL, f"Overloaded 3-winding transformers ({max_trafo_loading_pct=}):"
        )
        print_trafos_3w(overloaded_trafos_3w_ids)
    if overloaded_swing_buses_ids := get_overloaded_swing_buses_ids(
        max_swing_bus_power_mva
    ):
        v |= Violations.SWING_BUS_LOADING
        log.log(LOG_LEVEL, f"Overloaded swing buses ({max_swing_bus_power_mva=}):")
        print_swing_buses(overloaded_swing_buses_ids)
    log.log(
        logging.INFO if v == Violations.NO_VIOLATIONS else LOG_LEVEL,
        f"Detected violations: {v}\n",
    )
    return v


def run_solver(
    use_full_newton_raphson: bool,
    solver_opts: Optional[dict] = {"options1": 1, "options5": 1},
) -> None:
    """Default solver options:
    `options1=1` Use tap adjustment option setting
    `options5=1` Use switched shunt adjustment option setting
    """
    try:
        if not use_full_newton_raphson:
            wf.fdns(**solver_opts)
        else:
            wf.fnsl(**solver_opts)
    except PsseApiCallError as e:
        log.log(LOG_LEVEL, e.args)
    PowerFlows.increment_count()
