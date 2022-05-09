import dataclasses
from dataclasses import dataclass
from typing import Union

from pssetools.subsystems import Branch, Trafo, disable_branch, disable_trafo
from pssetools.violations_analysis import Violations, ViolationsLimits, check_violations


@dataclass
class ContingencyScenario:
    branches: tuple[Branch, ...]
    trafos: tuple[Trafo, ...]


LimitingSubsystem = Union[None, Branch, Trafo]


@dataclass
class LimitingFactor:
    v: Violations
    ss: LimitingSubsystem


def get_contingency_limiting_factor(
    contingency_scenario: ContingencyScenario,
    max_bus_voltage_pu: float = 1.12,
    min_bus_voltage_pu: float = 0.88,
    max_branch_loading_pct: float = 120.0,
    max_trafo_loading_pct: float = 120.0,
    max_swing_bus_power_mva: float = 1000.0,
    use_full_newton_raphson: bool = False,
) -> LimitingFactor:
    contingency_limits: ViolationsLimits = ViolationsLimits(
        max_bus_voltage_pu=max_bus_voltage_pu,
        min_bus_voltage_pu=min_bus_voltage_pu,
        max_branch_loading_pct=max_branch_loading_pct,
        max_trafo_loading_pct=max_trafo_loading_pct,
        max_swing_bus_power_mva=max_swing_bus_power_mva,
    )
    violations: Violations = Violations.NO_VIOLATIONS
    for branch in contingency_scenario.branches:
        if branch.is_enabled():
            with disable_branch(branch):
                violations |= check_violations(
                    **dataclasses.asdict(contingency_limits),
                    use_full_newton_raphson=use_full_newton_raphson
                )
                if violations != Violations.NO_VIOLATIONS:
                    return LimitingFactor(violations, branch)
    for trafo in contingency_scenario.trafos:
        if trafo.is_enabled():
            with disable_trafo(trafo):
                violations |= check_violations(
                    **dataclasses.asdict(contingency_limits),
                    use_full_newton_raphson=use_full_newton_raphson
                )
                if violations != Violations.NO_VIOLATIONS:
                    return LimitingFactor(violations, trafo)
    return LimitingFactor(violations, None)
