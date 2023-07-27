"""Grid capacity analysis

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
import dataclasses
import logging
from collections import OrderedDict, defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from pprint import pprint
from typing import Final, Iterator, Optional

from tqdm import tqdm

from gridcapacity.backends.subsystems import (
    Bus,
    Buses,
    Load,
    Loads,
    Machine,
    Machines,
    TemporaryBusLoad,
    TemporaryBusMachine,
    TemporaryBusSubsystem,
)
from gridcapacity.contingency_analysis import (
    ContingencyScenario,
    LimitingFactor,
    LimitingSubsystem,
    get_contingency_limiting_factor,
    get_contingency_scenario,
)
from gridcapacity.violations_analysis import (
    PowerFlows,
    Violations,
    ViolationsLimits,
    ViolationsStats,
    check_violations,
    run_solver,
)

from .backends import wrapped_funcs as wf
from .config import BusConnection, ConnectionScenario
from .utils import p_to_mva

log = logging.getLogger(__name__)


@dataclass
class BusHeadroom:
    bus: Bus
    actual_load_mva: complex
    actual_gen_mva: complex
    load_avail_mva: complex
    gen_avail_mva: complex
    load_lf: Optional[LimitingFactor]
    gen_lf: Optional[LimitingFactor]


Headroom = tuple[BusHeadroom, ...]


@dataclass(frozen=True)
class ContingencyCondition:
    power_mva: complex
    v: Violations


BusToContingencyConditions = dict[Bus, list[ContingencyCondition]]


def bus_to_contingency_conditions() -> BusToContingencyConditions:
    return defaultdict(list)


@dataclass(frozen=True)
class UnfeasibleCondition:
    power_mva: complex
    lf: LimitingFactor


SortedConnectionScenario = OrderedDict[int, BusConnection]


class CapacityAnalyser:
    """This class is made to simplify arguments passing
    between the capacity analysis steps:
     - loads analysis
     - max capacity analysis
     - feasibility check
     - getting limiting factor
    """

    def __init__(
        self,
        case_name: str,
        upper_load_limit_p_mw: float,
        upper_gen_limit_p_mw: float,
        load_power_factor: float,
        gen_power_factor: float,
        selected_buses_ids: Optional[Collection[int]],
        headroom_tolerance_p_mw: float,
        solver_opts: Optional[dict],
        max_iterations: int,
        normal_limits: Optional[ViolationsLimits],
        contingency_limits: Optional[ViolationsLimits],
        contingency_scenario: Optional[ContingencyScenario] = None,
        connection_scenario: Optional[ConnectionScenario] = None,
    ):
        self._case_name: str = case_name
        self._load_power_factor: float = load_power_factor
        self._gen_power_factor: float = gen_power_factor
        self._upper_load_limit_mva: Final[complex] = p_to_mva(
            upper_load_limit_p_mw, self._load_power_factor
        )
        self._upper_gen_limit_mva: Final[complex] = p_to_mva(
            upper_gen_limit_p_mw, self._gen_power_factor
        )
        self._selected_buses_ids: Optional[Collection[int]] = selected_buses_ids
        self._headroom_tolerance_p_mw: Final[float] = headroom_tolerance_p_mw
        self._solver_opts: Optional[dict] = solver_opts
        self._max_iterations: Final[int] = max_iterations
        self._normal_limits: Final[Optional[ViolationsLimits]] = normal_limits
        self._contingency_limits: Final[Optional[ViolationsLimits]] = contingency_limits
        self._connection_scenario: Optional[
            SortedConnectionScenario
        ] = sort_connection_scenario(connection_scenario)
        self._use_full_newton_raphson: Final[bool] = not self.fdns_is_applicable()
        self.check_base_case_violations()
        self._contingency_scenario: Final[
            ContingencyScenario
        ] = self.handle_empty_contingency_scenario(contingency_scenario)

    def fdns_is_applicable(self) -> bool:
        """Fixed slope Decoupled Newton-Raphson Solver (FDNS) is applicable"""
        self.reload_case()
        run_solver(use_full_newton_raphson=False, solver_opts=self._solver_opts)
        is_applicable: Final[bool] = wf.is_converged()
        if not is_applicable:
            # Reload the case and run power flow to get solution convergence
            # after failed FDNS
            self.reload_case()
            run_solver(use_full_newton_raphson=True, solver_opts=self._solver_opts)
        log.info("Case solved")
        return is_applicable

    def reload_case(self) -> None:
        wf.open_case(self._case_name)
        self.apply_connection_scenario()

    def apply_connection_scenario(self) -> None:
        if self._connection_scenario is None:
            return
        connections_iterator: Iterator = iter(self._connection_scenario.items())
        connections_available: bool = True
        bus_number = 0
        connection = BusConnection(load=None)
        try:
            bus_number, connection = next(connections_iterator)
        except StopIteration:
            connections_available = False
        for bus in Buses():
            if connections_available and bus.number == bus_number:
                if (load_connection := connection.load) is not None:
                    bus.add_load(
                        p_to_mva(load_connection.p_mw, load_connection.pf),
                        "CR",
                    )
                if (gen_connection := connection.gen) is not None:
                    bus.add_gen(
                        p_to_mva(gen_connection.p_mw, gen_connection.pf),
                        "CR",
                    )
                try:
                    bus_number, connection = next(connections_iterator)
                except StopIteration:
                    connections_available = False

    def check_base_case_violations(self) -> None:
        """Raise `RuntimeError` if base case has violations"""
        ViolationsStats.reset()
        CapacityAnalysisStats.reset()
        base_case_violations: Violations = self.check_violations()
        if base_case_violations & Violations.NOT_CONVERGED:
            raise RuntimeError(f"The base case has {base_case_violations}")
        ViolationsStats.register_base_case_violations()

    def handle_empty_contingency_scenario(
        self, contingency_scenario: Optional[ContingencyScenario]
    ) -> ContingencyScenario:
        """Returns new contingency scenario if none is provided"""
        if contingency_scenario is not None:
            return contingency_scenario
        contingency_scenario = get_contingency_scenario(
            use_full_newton_raphson=self._use_full_newton_raphson,
            solver_opts=self._solver_opts,
            contingency_limits=self._contingency_limits,
        )
        # Reopen file to fix potential solver problems after building contingency scenario
        self.reload_case()
        return contingency_scenario

    def buses_headroom(self) -> Headroom:
        """Return actual load and max additional PQ power in MVA for each bus"""
        buses: Buses = Buses()
        print("Analysing headroom")
        with tqdm(
            total=len(buses)
            if self._selected_buses_ids is None
            else len(self._selected_buses_ids),
            postfix=[{}],
        ) as progress:
            PowerFlows.reset_count()
            ViolationsStats.reset()
            return tuple(
                self.bus_headroom(bus, progress)
                for bus in buses
                if self._selected_buses_ids is None
                or bus.number in self._selected_buses_ids
            )

    def bus_headroom(self, bus: Bus, progress: tqdm) -> BusHeadroom:
        """Return bus actual load and max additional PQ power in MVA"""
        actual_load_mva: complex = bus.load_mva()
        actual_gen_mva: complex = bus.gen_mva()
        load_lf: Optional[LimitingFactor]
        load_available_mva: complex
        temp_load: TemporaryBusLoad = TemporaryBusLoad(bus)
        load_available_mva, load_lf = self.max_power_available_mva(
            temp_load, self._upper_load_limit_mva
        )
        if (
            load_available_mva == 0j
            and load_lf is not None
            and load_lf.v == Violations.NOT_CONVERGED
        ):
            self.reload_case()
        gen_available_mva: complex = 0j
        gen_lf: Optional[LimitingFactor] = None
        if actual_gen_mva != 0 and load_available_mva != 0j:
            temp_gen: TemporaryBusMachine = TemporaryBusMachine(bus)
            gen_available_mva, gen_lf = self.max_power_available_mva(
                temp_gen, self._upper_gen_limit_mva
            )
            if (
                gen_available_mva == 0j
                and gen_lf is not None
                and gen_lf.v == Violations.NOT_CONVERGED
            ):
                self.reload_case()
        progress.postfix[0]["bus_number"] = bus.number
        progress.postfix[0]["power_flows"] = PowerFlows.count
        progress.update()
        return BusHeadroom(
            bus=bus,
            actual_load_mva=actual_load_mva,
            actual_gen_mva=actual_gen_mva,
            load_avail_mva=load_available_mva,
            gen_avail_mva=gen_available_mva,
            load_lf=load_lf,
            gen_lf=gen_lf,
        )

    def max_power_available_mva(
        self,
        temp_subsystem: TemporaryBusSubsystem,
        upper_limit_mva: complex,
    ) -> tuple[complex, Optional[LimitingFactor]]:
        """Return max additional PQ power in MVA and a limiting factor"""
        lower_limit_mva: complex = 0j
        is_feasible: bool
        limiting_factor: Optional[LimitingFactor]
        # If upper limit is available, return it immediately
        with temp_subsystem(upper_limit_mva):
            is_feasible, limiting_factor = self.feasibility_check()
        if is_feasible:
            return upper_limit_mva, limiting_factor
        CapacityAnalysisStats.update(temp_subsystem, limiting_factor)
        self.reload_case()
        # First iteration was initial upper limit check. Subtract it.
        for _ in range(self._max_iterations - 1):
            middle_mva: complex = (lower_limit_mva + upper_limit_mva) / 2
            with temp_subsystem(middle_mva):
                is_feasible, limiting_factor = self.feasibility_check()
            if is_feasible:
                # Middle point is feasible: headroom is above
                lower_limit_mva = middle_mva
            else:
                # Middle point is NOT feasible: headroom is below
                upper_limit_mva = middle_mva
                CapacityAnalysisStats.update(temp_subsystem, limiting_factor)
                self.reload_case()
            if (
                upper_limit_mva.real - lower_limit_mva.real
                < self._headroom_tolerance_p_mw
            ):
                break
        return lower_limit_mva, limiting_factor

    def feasibility_check(self) -> tuple[bool, Optional[LimitingFactor]]:
        """Return `True` if feasible, else `False` with limiting factor"""
        violations: Violations
        limiting_factor: Optional[LimitingFactor]
        if (violations := self.check_violations()) != Violations.NO_VIOLATIONS:
            return False, LimitingFactor(violations, None)
        limiting_factor = self.contingency_check()
        if limiting_factor.v != Violations.NO_VIOLATIONS:
            return False, limiting_factor
        return True, None

    def check_violations(self) -> Violations:
        violations: Violations
        if self._normal_limits is None:
            violations = check_violations(
                use_full_newton_raphson=self._use_full_newton_raphson,
                solver_opts=self._solver_opts,
            )
        else:
            violations = check_violations(
                **dataclasses.asdict(self._normal_limits),
                use_full_newton_raphson=self._use_full_newton_raphson,
                solver_opts=self._solver_opts,
            )
        return violations

    def contingency_check(self) -> LimitingFactor:
        limiting_factor: LimitingFactor
        if self._contingency_limits is None:
            limiting_factor = get_contingency_limiting_factor(
                contingency_scenario=self._contingency_scenario,
                use_full_newton_raphson=self._use_full_newton_raphson,
            )
        else:
            limiting_factor = get_contingency_limiting_factor(
                contingency_scenario=self._contingency_scenario,
                use_full_newton_raphson=self._use_full_newton_raphson,
                contingency_limits=self._contingency_limits,
            )
        return limiting_factor


class CapacityAnalysisStats:
    _feasibility_stats: dict[Bus, list[UnfeasibleCondition]] = defaultdict(list)
    _contingency_stats: dict[
        LimitingSubsystem, BusToContingencyConditions
    ] = defaultdict(bus_to_contingency_conditions)

    @classmethod
    def update(
        cls,
        temp_subsystem: TemporaryBusSubsystem,
        limiting_factor: Optional[LimitingFactor],
    ) -> None:
        if limiting_factor is not None:
            power_mva: complex
            if isinstance(temp_subsystem, TemporaryBusLoad):
                power_mva = temp_subsystem.load_mva
            elif isinstance(temp_subsystem, TemporaryBusMachine):
                power_mva = -temp_subsystem.gen_mva
            else:
                raise TypeError(
                    f"Unexpected {type(temp_subsystem)=}, "
                    f"expected `TemporaryBusLoad` or `TemporaryBusMachine`"
                )
            cls._feasibility_stats[temp_subsystem.bus].append(
                UnfeasibleCondition(power_mva=power_mva, lf=limiting_factor)
            )
            if (subsystem := limiting_factor.ss) is not None:
                cls._contingency_stats[subsystem][temp_subsystem.bus].append(
                    ContingencyCondition(
                        power_mva=power_mva,
                        v=limiting_factor.v,
                    )
                )

    @classmethod
    def contingencies_dict(cls) -> dict:
        return cls._contingency_stats

    @classmethod
    def feasibility_dict(cls) -> dict:
        return cls._feasibility_stats

    @classmethod
    def print(cls) -> None:
        if len(cls._feasibility_stats.keys()):
            print()
            print(" FEASIBILITY STATS ".center(80, "="))
            for bus, unfeasible_conditions in cls._feasibility_stats.items():
                print(f"{bus}[{len(unfeasible_conditions)}]:")
                pprint(unfeasible_conditions)
        if len(cls._contingency_stats.keys()):
            print()
            print(" CONTINGENCIES STATS ".center(80, "="))
            for contingency, bus_to_contingency_conditions in sorted(
                cls._contingency_stats.items(),
                key=lambda items: sum(
                    len(contingency_conditions)
                    for contingency_conditions in items[1].values()
                ),
                reverse=True,
            ):
                print(
                    f"{contingency=}[{sum(len(violations) for violations in bus_to_contingency_conditions.values())}]:"
                )
                pprint(dict(bus_to_contingency_conditions))

    @classmethod
    def reset(cls) -> None:
        cls._feasibility_stats = defaultdict(list)
        cls._contingency_stats = defaultdict(bus_to_contingency_conditions)


def sort_connection_scenario(
    connection_scenario: Optional[ConnectionScenario],
) -> Optional[SortedConnectionScenario]:
    if connection_scenario is None:
        return None
    return OrderedDict(
        tuple(
            (int(k), v)
            for (k, v) in sorted(connection_scenario.items(), key=lambda kv: int(kv[0]))
        )
    )


def buses_headroom(
    case_name: str,
    upper_load_limit_p_mw: float,
    upper_gen_limit_p_mw: float,
    load_power_factor: float = 0.9,
    gen_power_factor: float = 0.9,
    selected_buses_ids: Optional[Collection[int]] = None,
    headroom_tolerance_p_mw: float = 5.0,
    solver_opts: Optional[dict] = None,
    max_iterations: int = 10,
    normal_limits: Optional[ViolationsLimits] = None,
    contingency_limits: Optional[ViolationsLimits] = None,
    contingency_scenario: Optional[ContingencyScenario] = None,
    connection_scenario: Optional[ConnectionScenario] = None,
) -> Headroom:
    """Return actual load and max additional PQ power in MVA for each bus."""
    capacity_analyser: CapacityAnalyser = CapacityAnalyser(
        case_name,
        upper_load_limit_p_mw,
        upper_gen_limit_p_mw,
        load_power_factor,
        gen_power_factor,
        selected_buses_ids,
        headroom_tolerance_p_mw,
        solver_opts,
        max_iterations,
        normal_limits,
        contingency_limits,
        contingency_scenario,
        connection_scenario,
    )
    return capacity_analyser.buses_headroom()
