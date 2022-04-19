import dataclasses
from dataclasses import dataclass

from pssetools.subsystems import (
    Branch,
    Branches,
    Trafo,
    Trafos,
    disable_branch,
    disable_trafo,
)
from pssetools.violations_analysis import Violations, ViolationsLimits, check_violations


@dataclass
class ContingencyScenario:
    branches: tuple[Branch, ...]
    trafos: tuple[Trafo, ...]


def get_contingency_scenario(
    max_bus_voltage_pu: float = 1.12,
    min_bus_voltage_pu: float = 0.88,
    max_branch_loading_pct: float = 120.0,
    max_trafo_loading_pct: float = 120.0,
    max_swing_bus_power_mva: float = 1000.0,
    use_full_newton_raphson: bool = False,
) -> ContingencyScenario:
    contingency_limits: ViolationsLimits = ViolationsLimits(
        max_bus_voltage_pu=max_bus_voltage_pu,
        min_bus_voltage_pu=min_bus_voltage_pu,
        max_branch_loading_pct=max_branch_loading_pct,
        max_trafo_loading_pct=max_trafo_loading_pct,
        max_swing_bus_power_mva=max_swing_bus_power_mva,
    )
    not_critical_branches: tuple[Branch, ...] = tuple(
        branch
        for branch in Branches()
        if branch_is_not_critical(branch, contingency_limits, use_full_newton_raphson)
    )
    not_critical_trafos: tuple[Trafo, ...] = tuple(
        trafo
        for trafo in Trafos()
        if trafo_is_not_critical(trafo, contingency_limits, use_full_newton_raphson)
    )
    return ContingencyScenario(not_critical_branches, not_critical_trafos)


def branch_is_not_critical(
    branch: Branch,
    contingency_limits: ViolationsLimits,
    use_full_newton_raphson: bool,
) -> bool:
    if branch.is_enabled():
        with disable_branch(branch) as is_disabled:
            if is_disabled:
                violations: Violations = check_violations(
                    **dataclasses.asdict(contingency_limits),
                    use_full_newton_raphson=use_full_newton_raphson
                )
                return violations == Violations.NO_VIOLATIONS
    return False


def trafo_is_not_critical(
    trafo: Trafo,
    contingency_limits: ViolationsLimits,
    use_full_newton_raphson: bool,
) -> bool:
    if trafo.is_enabled():
        with disable_trafo(trafo) as is_disabled:
            if is_disabled:
                violations: Violations = check_violations(
                    **dataclasses.asdict(contingency_limits),
                    use_full_newton_raphson=use_full_newton_raphson
                )
            return violations == Violations.NO_VIOLATIONS
    return False


def contingency_check(
    contingency_scenario: ContingencyScenario,
    max_bus_voltage_pu: float = 1.12,
    min_bus_voltage_pu: float = 0.88,
    max_branch_loading_pct: float = 120.0,
    max_trafo_loading_pct: float = 120.0,
    max_swing_bus_power_mva: float = 1000.0,
    use_full_newton_raphson: bool = False,
) -> Violations:
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
                    return violations
    for trafo in contingency_scenario.trafos:
        if trafo.is_enabled():
            with disable_trafo(trafo):
                violations |= check_violations(
                    **dataclasses.asdict(contingency_limits),
                    use_full_newton_raphson=use_full_newton_raphson
                )
                if violations != Violations.NO_VIOLATIONS:
                    return violations
    return violations
