"""Grid capacity analysis"""
import dataclasses
import math
from collections.abc import Collection
from dataclasses import dataclass
from typing import Final, Iterator, Optional, Union

from tqdm import tqdm

from pssetools.contingency_analysis import (
    ContingencyScenario,
    LimitingSubsystem,
    contingency_check,
    get_contingency_limiting_subsystem,
    get_contingency_scenario,
)
from pssetools.subsystems import (
    Branch,
    Bus,
    Buses,
    Load,
    Loads,
    TemporaryBusLoad,
    Trafo,
)
from pssetools.violations_analysis import Violations, ViolationsLimits, check_violations


@dataclass
class LimitingFactor:
    v: Violations
    ss: LimitingSubsystem


@dataclass
class BusHeadroom:
    bus: Bus
    actual_load_mva: complex
    bus_capacity_available_mva: complex
    lf: Optional[LimitingFactor]


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
        upper_limit_p_mw: float,
        power_factor: float,
        selected_buses_ids: Optional[Collection[int]],
        solver_tolerance_p_mw: float,
        max_iterations: int,
        normal_limits: Optional[ViolationsLimits],
        contingency_limits: Optional[ViolationsLimits],
        contingency_scenario: ContingencyScenario,
        use_full_newton_raphson: bool,
    ):
        upper_limit_q_mw: Final[float] = upper_limit_p_mw * math.tan(
            math.acos(power_factor)
        )
        self._upper_limit_mva: Final[complex] = upper_limit_p_mw + 1j * upper_limit_q_mw
        self._upper_limit_p_mw: Final[float] = upper_limit_p_mw
        self._q_to_p_ratio: Final[float] = power_factor
        self._selected_buses_ids: Optional[Collection[int]] = selected_buses_ids
        self._solver_tolerance_p_mw: Final[float] = solver_tolerance_p_mw
        self._max_iterations: Final[int] = max_iterations
        self._normal_limits: Final[Optional[ViolationsLimits]] = normal_limits
        self._contingency_limits: Final[Optional[ViolationsLimits]] = contingency_limits
        self._contingency_scenario: Final[ContingencyScenario] = contingency_scenario
        self._use_full_newton_raphson: Final[bool] = use_full_newton_raphson
        self._loads_iterator: Iterator = iter(Loads())
        self._loads_available: bool = True
        try:
            self._load: Load = next(self._loads_iterator)
        except StopIteration:
            self._loads_available = False

    def buses_headroom(self) -> tuple[BusHeadroom, ...]:
        """Return actual load and max additional PQ power in MVA for each bus"""
        buses: Buses = Buses()
        print("Analysing headroom")
        with tqdm(
            total=len(buses)
            if self._selected_buses_ids is None
            else len(self._selected_buses_ids),
            postfix=[{}],
        ) as progress:
            return tuple(
                self.bus_headroom(bus, progress)
                for bus in buses
                if self._selected_buses_ids is None
                or bus.number in self._selected_buses_ids
            )

    def bus_headroom(self, bus: Bus, progress: tqdm) -> BusHeadroom:
        """Return bus actual load and max additional PQ power in MVA"""
        actual_load_mva: complex = self.bus_actual_load_mva(bus.number)
        bus_capacity_available_mva: complex = self.max_bus_capacity_mva(
            bus,
        )
        limiting_factor: Optional[LimitingFactor] = None
        if bus_capacity_available_mva == 0j:
            limiting_factor = self.get_limiting_factor(bus)
        progress.postfix[0]["bus_number"] = bus.number
        progress.update()
        return BusHeadroom(
            bus, actual_load_mva, bus_capacity_available_mva, limiting_factor
        )

    def bus_actual_load_mva(self, bus_number: int) -> complex:
        """Return sum of all bus loads"""
        actual_load_mva: complex = 0j
        # Buses and loads are sorted by bus number [PSSE API.pdf].
        # So loads are iterated until load bus number is lower or equal
        # to the bus number.
        while self._loads_available and self._load.number <= bus_number:
            if self._load.number == bus_number:
                actual_load_mva += self._load.mva_act
            try:
                self._load = next(self._loads_iterator)
            except StopIteration:
                self._loads_available = False
        return actual_load_mva

    def max_bus_capacity_mva(
        self,
        bus: Bus,
    ) -> complex:
        """Return max additional load PQ power in MVA"""
        upper_limit_mva: complex = self._upper_limit_mva
        lower_limit_mva: complex = 0j
        temp_load: TemporaryBusLoad = TemporaryBusLoad(bus)
        with temp_load:
            # If upper limit is available, return it immediately
            temp_load(upper_limit_mva)
            if self.is_feasible():
                return upper_limit_mva
            # First iteration was initial upper limit check. Subtract it.
            for i in range(self._max_iterations - 1):
                middle_mva: complex = (lower_limit_mva + upper_limit_mva) / 2
                temp_load(middle_mva)
                if self.is_feasible():
                    # Middle point is feasible: headroom is above
                    lower_limit_mva = middle_mva
                else:
                    # Middle point is NOT feasible: headroom is below
                    upper_limit_mva = middle_mva
                if (
                    upper_limit_mva.real - lower_limit_mva.real
                    < self._solver_tolerance_p_mw
                ):
                    break
        return lower_limit_mva

    def is_feasible(self) -> bool:
        """Return `True` if feasible"""
        violations: Violations
        if self._normal_limits is None:
            violations = check_violations(
                use_full_newton_raphson=self._use_full_newton_raphson
            )
        else:
            violations = check_violations(
                **dataclasses.asdict(self._normal_limits),
                use_full_newton_raphson=self._use_full_newton_raphson,
            )
        if violations == Violations.NO_VIOLATIONS:
            if self._contingency_limits is None:
                violations = contingency_check(
                    contingency_scenario=self._contingency_scenario,
                    use_full_newton_raphson=self._use_full_newton_raphson,
                )
            else:
                violations = contingency_check(
                    contingency_scenario=self._contingency_scenario,
                    **dataclasses.asdict(self._contingency_limits),
                    use_full_newton_raphson=self._use_full_newton_raphson,
                )
        return violations == Violations.NO_VIOLATIONS

    def get_limiting_factor(self, bus: Bus) -> LimitingFactor:
        temp_load: TemporaryBusLoad = TemporaryBusLoad(bus)
        with temp_load:
            # If upper limit is available, return it immediately
            temp_load(self._upper_limit_mva)
            violations: Violations
            limiting_subsystem: LimitingSubsystem
            if self._normal_limits is None:
                violations = check_violations(
                    use_full_newton_raphson=self._use_full_newton_raphson
                )
            else:
                violations = check_violations(
                    **dataclasses.asdict(self._normal_limits),
                    use_full_newton_raphson=self._use_full_newton_raphson,
                )
            if violations != Violations.NO_VIOLATIONS:
                limiting_subsystem = None
            else:
                if self._contingency_limits is None:
                    limiting_subsystem = get_contingency_limiting_subsystem(
                        contingency_scenario=self._contingency_scenario,
                        use_full_newton_raphson=self._use_full_newton_raphson,
                    )
                else:
                    limiting_subsystem = get_contingency_limiting_subsystem(
                        contingency_scenario=self._contingency_scenario,
                        **dataclasses.asdict(self._contingency_limits),
                        use_full_newton_raphson=self._use_full_newton_raphson,
                    )
            return LimitingFactor(v=violations, ss=limiting_subsystem)


def buses_headroom(
    upper_limit_p_mw: float,
    power_factor: float = 0.9,
    selected_buses_ids: Optional[Collection[int]] = None,
    solver_tolerance_p_mw: float = 5.0,
    max_iterations: int = 10,
    normal_limits: Optional[ViolationsLimits] = None,
    contingency_limits: Optional[ViolationsLimits] = None,
    contingency_scenario: Optional[ContingencyScenario] = None,
    use_full_newton_raphson: bool = False,
) -> tuple[BusHeadroom, ...]:
    """Return actual load and max additional PQ power in MVA for each bus"""
    capacity_analyser: CapacityAnalyser = CapacityAnalyser(
        upper_limit_p_mw,
        power_factor,
        selected_buses_ids,
        solver_tolerance_p_mw,
        max_iterations,
        normal_limits,
        contingency_limits,
        contingency_scenario
        if contingency_scenario is not None
        else get_contingency_scenario(),
        use_full_newton_raphson,
    )
    return capacity_analyser.buses_headroom()
