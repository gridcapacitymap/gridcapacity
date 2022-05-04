import enum
import logging
import os
from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from typing import Final

import psspy

from pssetools import wrapped_funcs as wf
from pssetools.subsystem_data import (
    get_overloaded_branches_ids,
    get_overloaded_swing_buses_ids,
    get_overloaded_trafos_3w_ids,
    get_overloaded_trafos_ids,
    print_branches,
    print_buses,
    print_swing_buses,
    print_trafos,
    print_trafos_3w,
)
from pssetools.subsystems import Buses
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
    TRAFO_3W_LOADING = enum.auto()
    SWING_BUS_LOADING = enum.auto()


@dataclass
class ViolationsLimits:
    max_bus_voltage_pu: float
    min_bus_voltage_pu: float
    max_branch_loading_pct: float
    max_trafo_loading_pct: float
    max_swing_bus_power_mva: float


SubsystemIdxToViolationValues = dict[int, list[float]]
LimitValueToSubsystem = dict[float, SubsystemIdxToViolationValues]
ViolationTypeToLimitValue = dict[Violations, LimitValueToSubsystem]


def limit_value_to_subsystem() -> LimitValueToSubsystem:
    def subsystem_idx_to_violation_values() -> SubsystemIdxToViolationValues:
        return defaultdict(list)

    return defaultdict(subsystem_idx_to_violation_values)


class ViolationsStats:
    _violations_stats: ViolationTypeToLimitValue = defaultdict(limit_value_to_subsystem)

    @classmethod
    def reset(cls) -> None:
        cls._violations_stats = defaultdict(limit_value_to_subsystem)

    @classmethod
    def is_empty(cls):
        return len(cls._violations_stats.keys()) == 0

    @classmethod
    def append_violations(
        cls,
        violation: Violations,
        limit_value: float,
        subsystem_indexes: Collection[int],
        violated_values: Collection[float],
    ):
        for subsystem_index, violated_value in zip(subsystem_indexes, violated_values):
            cls._violations_stats[violation][limit_value][subsystem_index].append(
                violated_value
            )

    @classmethod
    def print(cls) -> None:
        for violation, limit_value_to_ss_violations in cls._violations_stats.items():
            subsystem: Buses
            if (
                violation == Violations.BUS_OVERVOLTAGE
                or violation == Violations.BUS_UNDERVOLTAGE
            ):
                subsystem = Buses()
            else:
                raise RuntimeError(f"Unknown {violation=}")

            for limit, ss_violations in sorted(
                limit_value_to_ss_violations.items(),
                key=lambda items: items[0],
                reverse=True,
            ):
                print(f"{violation} {limit=}")
                for ss_idx, violated_values in sorted(
                    ss_violations.items(), key=lambda items: max(items[1]), reverse=True
                ):
                    print(
                        f"{subsystem[ss_idx]}: {tuple(sorted(violated_values, reverse=True))}"
                    )


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
    solver_opts: dict = {"options1": 1, "options5": 1},
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
    buses: Buses = Buses()
    if overvoltage_buses_indexes := buses.get_overvoltage_indexes(max_bus_voltage_pu):
        v |= Violations.BUS_OVERVOLTAGE
        log.log(LOG_LEVEL, f"Overvoltage buses ({max_bus_voltage_pu=}):")
        buses.log(LOG_LEVEL, overvoltage_buses_indexes)
        ViolationsStats.append_violations(
            Violations.BUS_OVERVOLTAGE,
            max_bus_voltage_pu,
            overvoltage_buses_indexes,
            buses.get_voltage_pu(overvoltage_buses_indexes),
        )
    if undervoltage_buses_indexes := buses.get_undervoltage_indexes(min_bus_voltage_pu):
        v |= Violations.BUS_UNDERVOLTAGE
        log.log(LOG_LEVEL, f"Undervoltage buses ({min_bus_voltage_pu=}):")
        buses.log(LOG_LEVEL, undervoltage_buses_indexes)
        ViolationsStats.append_violations(
            Violations.BUS_UNDERVOLTAGE,
            min_bus_voltage_pu,
            undervoltage_buses_indexes,
            buses.get_voltage_pu(undervoltage_buses_indexes),
        )
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
        v |= Violations.TRAFO_3W_LOADING
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
    solver_opts: dict = {"options1": 1, "options5": 1},
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
