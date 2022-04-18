"""Grid capacity analysis"""
import dataclasses
from dataclasses import dataclass
from typing import Final, Iterator, Optional

from tqdm import tqdm

from pssetools.contingency_analysis import ContingencyScenario, contingency_check
from pssetools.subsystems import Bus, Buses, Load, Loads, TemporaryBusLoad
from pssetools.violations_analysis import Violations, ViolationsLimits, check_violations


@dataclass
class BusHeadroom:
    bus: Bus
    actual_load_mw: complex
    bus_capacity_available_mw: complex


class CapacityAnalyser:
    """This class is made to simplify arguments passing
    between the capacity analysis steps:
     - loads analysis
     - max capacity analysis
     - feasibility check
    """

    def __init__(
        self,
        upper_limit_p_mw: float,
        q_to_p_ratio: float,
        solver_tolerance_p_mw: float,
        max_iterations: int,
        normal_limits: Optional[ViolationsLimits],
        contingency_limits: Optional[ViolationsLimits],
        contingency_scenario: ContingencyScenario,
        use_full_newton_raphson: bool,
    ):
        self._upper_limit_p_mw: Final[float] = upper_limit_p_mw
        self._q_to_p_ratio: Final[float] = q_to_p_ratio
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
        """Return actual load and max additional PQ power in MW for each bus"""
        buses: Buses = Buses()
        print("Analysing headroom")
        with tqdm(
            total=len(buses),
            postfix=[{}],
        ) as progress:
            return tuple(self.bus_headroom(bus, progress) for bus in buses)

    def bus_headroom(self, bus: Bus, progress: tqdm) -> BusHeadroom:
        """Return bus actual load and max additional PQ power in MW"""
        actual_load_pq_mw: complex = self.bus_actual_load_pq_mw(bus.number)
        upper_limit_pq_mw: complex = self.bus_upper_limit_pq_mw(actual_load_pq_mw)
        bus_capacity_available_mw: complex = self.max_bus_capacity_pq_mw(
            bus,
            upper_limit_pq_mw,
        )
        progress.postfix[0]["bus_number"] = bus.number
        progress.update()
        return BusHeadroom(bus, actual_load_pq_mw, bus_capacity_available_mw)

    def bus_actual_load_pq_mw(self, bus_number: int) -> complex:
        """Return sum of all bus loads"""
        actual_load_pq_mw: complex = 0j
        # Buses and loads are sorted by bus number [PSSE API.pdf].
        # So loads are iterated until load bus number is lower or equal
        # to the bus number.
        while self._loads_available and self._load.number <= bus_number:
            if self._load.number == bus_number:
                actual_load_pq_mw += self._load.mva_act
            try:
                self._load = next(self._loads_iterator)
            except StopIteration:
                self._loads_available = False
        return actual_load_pq_mw

    def bus_upper_limit_pq_mw(self, actual_load_pq_mw: complex) -> complex:
        """The active power (P) is fixed.
        The reactive power (Q) is proportional to the bus load
        if the latter exists."""
        upper_limit_q_mw: float
        if actual_load_pq_mw.real == 0:
            upper_limit_q_mw = self._q_to_p_ratio * self._upper_limit_p_mw
        else:
            actual_q_to_p_ratio: float = actual_load_pq_mw.imag / actual_load_pq_mw.real
            upper_limit_q_mw = actual_q_to_p_ratio * self._upper_limit_p_mw
        return self._upper_limit_p_mw + (upper_limit_q_mw * 1j)

    def max_bus_capacity_pq_mw(
        self,
        bus: Bus,
        upper_limit_pq_mw: complex,
    ) -> complex:
        """Return max additional load PQ power in MW"""
        lower_limit_pq_mw: complex = 0j
        temp_load: TemporaryBusLoad = TemporaryBusLoad(bus)
        with temp_load:
            # If upper limit is available, return it immediately
            temp_load(upper_limit_pq_mw)
            if self.is_feasible():
                return upper_limit_pq_mw
            # First iteration was initial upper limit check. Subtract it.
            for i in range(self._max_iterations - 1):
                middle_pq_mw: complex = (lower_limit_pq_mw + upper_limit_pq_mw) / 2
                temp_load(middle_pq_mw)
                if self.is_feasible():
                    # Middle point is feasible: headroom is above
                    lower_limit_pq_mw = middle_pq_mw
                else:
                    # Middle point is NOT feasible: headroom is below
                    upper_limit_pq_mw = middle_pq_mw
                if (
                    upper_limit_pq_mw.real - lower_limit_pq_mw.real
                    < self._solver_tolerance_p_mw
                ):
                    break
        return lower_limit_pq_mw

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


def buses_headroom(
    upper_limit_p_mw: float,
    q_to_p_ratio: float = 0.8,
    solver_tolerance_p_mw: float = 5.0,
    max_iterations: int = 10,
    normal_limits: Optional[ViolationsLimits] = None,
    contingency_limits: Optional[ViolationsLimits] = None,
    contingency_scenario: ContingencyScenario = ContingencyScenario(()),
    use_full_newton_raphson: bool = False,
) -> tuple[BusHeadroom, ...]:
    """Return actual load and max additional PQ power in MW for each bus"""
    capacity_analyser: CapacityAnalyser = CapacityAnalyser(
        upper_limit_p_mw,
        q_to_p_ratio,
        solver_tolerance_p_mw,
        max_iterations,
        normal_limits,
        contingency_limits,
        contingency_scenario,
        use_full_newton_raphson,
    )
    return capacity_analyser.buses_headroom()
