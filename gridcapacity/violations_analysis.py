"""
Copyright 2022 Vattenfall AB

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import enum
import logging
import os
from collections import defaultdict
from collections.abc import Callable, Collection
from dataclasses import dataclass
from typing import Final, Optional

from gridcapacity.backends import wrapped_funcs as wf
from gridcapacity.backends.subsystems import (
    Branches,
    Buses,
    Subsystems,
    SwingBuses,
    Trafos,
    Trafos3w,
)

log = logging.getLogger(__name__)
LOG_LEVEL: Final[int] = (
    logging.INFO
    if not os.getenv("GRID_CAPACITY_TREAT_VIOLATIONS_AS_WARNINGS")
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
    max_swing_bus_power_p_mw: float
    branch_rate: str
    trafo_rate: str


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
    def asdict(cls) -> dict:
        return cls._violations_stats

    @classmethod
    def is_empty(cls) -> bool:
        return len(cls._violations_stats.keys()) == 0

    @classmethod
    def append_violations(
        cls,
        violation: Violations,
        limit: float,
        subsystems: Subsystems,
        violated_subsystem_indexes: tuple[int, ...],
    ) -> None:
        log.log(LOG_LEVEL, f"{violation} {limit=} ")
        subsystems.log(LOG_LEVEL, violated_subsystem_indexes)
        violated_values: tuple[float, ...]
        if isinstance(subsystems, Buses):
            violated_values = subsystems.get_voltage_pu(violated_subsystem_indexes)
        elif isinstance(subsystems, SwingBuses):
            violated_values = subsystems.get_power_p_mw(violated_subsystem_indexes)
        else:
            violated_values = subsystems.get_loading_pct(violated_subsystem_indexes)
        for subsystem_index, violated_value in zip(
            violated_subsystem_indexes, violated_values
        ):
            cls._violations_stats[violation][limit][subsystem_index].append(
                violated_value
            )

    @classmethod
    def _get_subsystems_for_violation(cls, violation: Violations) -> Subsystems:
        subsystems: Subsystems
        if (
            violation == Violations.BUS_OVERVOLTAGE
            or violation == Violations.BUS_UNDERVOLTAGE
        ):
            subsystems = Buses()
        elif violation == Violations.BRANCH_LOADING:
            subsystems = Branches()
        elif violation == Violations.TRAFO_LOADING:
            subsystems = Trafos()
        elif violation == Violations.TRAFO_3W_LOADING:
            subsystems = Trafos3w()
        elif violation == Violations.SWING_BUS_LOADING:
            subsystems = SwingBuses()
        else:
            raise RuntimeError(f"Unknown {violation=}")
        return subsystems

    @classmethod
    def print(cls) -> None:
        for violation, limit_value_to_ss_violations in cls._violations_stats.items():
            subsystems: Subsystems = cls._get_subsystems_for_violation(violation)
            sort_values_descending: bool
            collection_reducer: Callable[[Collection[float]], float]
            if violation != Violations.BUS_UNDERVOLTAGE:
                sort_values_descending = True
                collection_reducer = max
            else:
                sort_values_descending = False
                collection_reducer = min
            for limit, ss_violations in sorted(
                limit_value_to_ss_violations.items(),
                key=lambda items: items[0],
                reverse=sort_values_descending,
            ):
                print(f" {violation} {limit=} ".center(80, "-"))
                for ss_idx, violated_values in sorted(
                    ss_violations.items(),
                    key=lambda items: collection_reducer(items[1]),
                    reverse=sort_values_descending,
                ):
                    print(
                        f"{subsystems[ss_idx]}: {tuple(sorted(violated_values, reverse=sort_values_descending))}"
                    )


def check_violations(
    max_bus_voltage_pu: float = 1.1,
    min_bus_voltage_pu: float = 0.9,
    max_branch_loading_pct: float = 100.0,
    max_trafo_loading_pct: float = 100.0,
    max_swing_bus_power_p_mw: float = 1000.0,
    branch_rate: str = "Rate1",
    trafo_rate: str = "Rate1",
    use_full_newton_raphson: bool = False,
    solver_opts: Optional[dict] = None,
) -> Violations:
    run_solver(use_full_newton_raphson, solver_opts)
    v: Violations = Violations.NO_VIOLATIONS
    if not wf.is_converged():
        v |= Violations.NOT_CONVERGED
        log.log(LOG_LEVEL, "Case not solved!")
        return v
    log.info(f"\nCHECKING VIOLATIONS")
    buses: Buses = Buses()
    if overvoltage_buses_indexes := buses.get_overvoltage_indexes(max_bus_voltage_pu):
        v |= Violations.BUS_OVERVOLTAGE
        ViolationsStats.append_violations(
            Violations.BUS_OVERVOLTAGE,
            max_bus_voltage_pu,
            buses,
            overvoltage_buses_indexes,
        )
    if undervoltage_buses_indexes := buses.get_undervoltage_indexes(min_bus_voltage_pu):
        v |= Violations.BUS_UNDERVOLTAGE
        ViolationsStats.append_violations(
            Violations.BUS_UNDERVOLTAGE,
            min_bus_voltage_pu,
            buses,
            undervoltage_buses_indexes,
        )
    branches: Branches = Branches(branch_rate)
    if overloaded_branches_indexes := branches.get_overloaded_indexes(
        max_branch_loading_pct
    ):
        v |= Violations.BRANCH_LOADING
        ViolationsStats.append_violations(
            Violations.BRANCH_LOADING,
            max_branch_loading_pct,
            branches,
            overloaded_branches_indexes,
        )
    trafos: Trafos = Trafos(trafo_rate)
    if overloaded_trafos_indexes := trafos.get_overloaded_indexes(
        max_trafo_loading_pct
    ):
        v |= Violations.TRAFO_LOADING
        ViolationsStats.append_violations(
            Violations.TRAFO_LOADING,
            max_trafo_loading_pct,
            trafos,
            overloaded_trafos_indexes,
        )
    trafos3w: Trafos3w = Trafos3w(trafo_rate)
    if overloaded_trafos3w_indexes := trafos3w.get_overloaded_indexes(
        max_trafo_loading_pct
    ):
        v |= Violations.TRAFO_3W_LOADING
        ViolationsStats.append_violations(
            Violations.TRAFO_3W_LOADING,
            max_trafo_loading_pct,
            trafos3w,
            overloaded_trafos3w_indexes,
        )
    swing_buses: SwingBuses = SwingBuses()
    if overloaded_swing_buses_indexes := swing_buses.get_overloaded_indexes(
        max_swing_bus_power_p_mw
    ):
        v |= Violations.SWING_BUS_LOADING
        ViolationsStats.append_violations(
            Violations.SWING_BUS_LOADING,
            max_swing_bus_power_p_mw,
            swing_buses,
            overloaded_swing_buses_indexes,
        )
    return v


def run_solver(
    use_full_newton_raphson: bool,
    solver_opts: Optional[dict] = None,
) -> None:
    wf.run_solver(use_full_newton_raphson, solver_opts)
    PowerFlows.increment_count()
