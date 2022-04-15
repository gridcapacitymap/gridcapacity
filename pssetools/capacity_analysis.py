import dataclasses
from dataclasses import dataclass
from typing import Iterator, Optional

from tqdm import tqdm

from pssetools.subsystems import Bus, Buses, Load, Loads
from pssetools.violations_analysis import Violations, ViolationsLimits, check_violations


def is_feasible(
    normal_limits: Optional[ViolationsLimits] = None,
    contingency_limits: Optional[ViolationsLimits] = None,
    contingency_scenario=None,
    use_full_newton_raphson: bool = False,
) -> bool:
    """Return `True` if feasible"""
    violations: Violations
    if normal_limits is None:
        violations = check_violations(use_full_newton_raphson=use_full_newton_raphson)
    else:
        violations = check_violations(
            **dataclasses.asdict(normal_limits),
            use_full_newton_raphson=use_full_newton_raphson,
        )
    return violations == Violations.NO_VIOLATIONS


def max_load_capacity_pq_mw(
    load: Load,
    upper_limit_pq_mw: complex,
    solver_tolerance_p_mw: float = 5.0,
    max_iterations: int = 10,
    normal_limits: Optional[ViolationsLimits] = None,
    contingency_limits: Optional[ViolationsLimits] = None,
    contingency_scenario=None,
    use_full_newton_raphson: bool = False,
) -> complex:
    """Return max additional load PQ power in MW"""
    lower_limit_pq_mw: complex = 0j
    with load:
        # If upper limit is available, return it immediately
        load.set_additional_load(upper_limit_pq_mw)
        if is_feasible(
            normal_limits,
            contingency_limits,
            contingency_scenario,
            use_full_newton_raphson,
        ):
            return upper_limit_pq_mw
        # First iteration was initial upper limit check. Subtract it.
        for i in range(max_iterations - 1):
            middle_pq_mw: complex = (lower_limit_pq_mw + upper_limit_pq_mw) / 2
            load.set_additional_load(middle_pq_mw)
            if is_feasible(
                normal_limits,
                contingency_limits,
                contingency_scenario,
                use_full_newton_raphson,
            ):
                # Middle point is feasible: headroom is above
                lower_limit_pq_mw = middle_pq_mw
            else:
                # Middle point is NOT feasible: headroom is below
                upper_limit_pq_mw = middle_pq_mw
            if upper_limit_pq_mw.real - lower_limit_pq_mw.real < solver_tolerance_p_mw:
                break
    return lower_limit_pq_mw


@dataclass
class BusHeadroom:
    bus: Bus
    actual_load_mw: complex
    bus_capacity_available_mw: complex


def buses_headroom(
    upper_limit_p_mw: float,
    solver_tolerance_p_mw: float = 5.0,
    max_iterations: int = 10,
    normal_limits: Optional[ViolationsLimits] = None,
    contingency_limits: Optional[ViolationsLimits] = None,
    contingency_scenario=None,
    use_full_newton_raphson: bool = False,
) -> list[BusHeadroom]:
    """Return bus actual load and max additional power in MW"""
    headroom: list[BusHeadroom] = []
    buses: Buses = Buses()
    print("Analysing headroom")
    with tqdm(
        total=len(buses),
        postfix=[{}],
    ) as progress:
        loads_available: bool = True
        try:
            loads_iterator: Iterator = iter(Loads())
            load: Load = next(loads_iterator)
        except StopIteration:
            loads_available = False
        for bus in buses:
            bus_actual_load_mw: complex = 0j
            last_load: Load
            while loads_available and load.number <= bus.number:
                if load.number == bus.number:
                    bus_actual_load_mw += load.mva_act
                    last_load = load
                try:
                    load = next(loads_iterator)
                except StopIteration:
                    loads_available = False
            bus_capacity_available_mw: complex = 0j
            if bus_actual_load_mw != 0j:
                q_to_p_ratio: float = bus_actual_load_mw.imag / bus_actual_load_mw.real
                bus_capacity_available_mw = max_load_capacity_pq_mw(
                    last_load,
                    upper_limit_p_mw + (q_to_p_ratio * upper_limit_p_mw * 1j),
                    solver_tolerance_p_mw,
                    max_iterations,
                    normal_limits,
                    contingency_limits,
                    contingency_scenario,
                    use_full_newton_raphson,
                )
            headroom.append(
                BusHeadroom(bus, bus_actual_load_mw, bus_capacity_available_mw)
            )
            progress.postfix[0]["bus_number"] = bus.number
            progress.update()
    return headroom
