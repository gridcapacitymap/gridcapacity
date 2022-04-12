import dataclasses
from typing import Optional, Final

from pssetools.subsystems import Load, Loads
from pssetools.violations_analysis import Violations, ViolationsLimits, check_violations


def feasibility_check(
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
    is_feasible: bool = violations == Violations.NO_VIOLATIONS
    return is_feasible


def max_capacity_pu(
    load: Load,
    upper_limit_mw: float,
    solver_tolerance_mw: float = 5.0,
    normal_limits: Optional[ViolationsLimits] = None,
    contingency_limits: Optional[ViolationsLimits] = None,
    contingency_scenario=None,
    use_full_newton_raphson: bool = False,
) -> float:
    """Return max power in per-units of actual load"""
    upper_limit_pu: float = (upper_limit_mw + load.mva_act.real) / load.mva_act.real
    lower_limit_pu: float = 1.0
    solver_tolerance_pu: Final[float] = solver_tolerance_mw / load.mva_act.real
    with load:
        # If upper limit is available, return immediately
        load.set_multiplier(upper_limit_pu)
        if feasibility_check(
            normal_limits,
            contingency_limits,
            contingency_scenario,
            use_full_newton_raphson,
        ):
            return upper_limit_pu
        for i in range(9):
            middle_pu: float = (lower_limit_pu + upper_limit_pu) / 2
            load.set_multiplier(middle_pu)
            if feasibility_check(
                normal_limits,
                contingency_limits,
                contingency_scenario,
                use_full_newton_raphson,
            ):
                # Middle point is feasible: headroom is above
                lower_limit_pu = middle_pu
            else:
                # Middle point is NOT feasible: headroom is below
                upper_limit_pu = middle_pu
            if upper_limit_pu - lower_limit_pu < solver_tolerance_pu:
                break
    return lower_limit_pu


def headroom(
    upper_limit_p_mw: float,
    solver_tolerance_mw: float = 5.0,
    normal_limits: Optional[ViolationsLimits] = None,
    contingency_limits: Optional[ViolationsLimits] = None,
    contingency_scenario=None,
    use_full_newton_raphson: bool = False,
) -> dict[Load, float]:
    """Return dict of load to max additional active power in MW"""
    headroom_dict: dict[Load, float] = {}
    for load in Loads():
        load_max_capacity_pu: float = max_capacity_pu(
            load,
            upper_limit_p_mw,
            solver_tolerance_mw,
            normal_limits,
            contingency_limits,
            contingency_scenario,
            use_full_newton_raphson,
        )
        headroom_dict[load] = (load_max_capacity_pu - 1.0) * load.mva_act.real
    return headroom_dict
