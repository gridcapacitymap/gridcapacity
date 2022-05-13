import dataclasses
from dataclasses import dataclass
from typing import Optional, Union

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
    branch_rate: str = "Rate2",
    trafo_rate: str = "Rate1",
    use_full_newton_raphson: bool = False,
) -> LimitingFactor:
    contingency_limits: ViolationsLimits = ViolationsLimits(
        max_bus_voltage_pu=max_bus_voltage_pu,
        min_bus_voltage_pu=min_bus_voltage_pu,
        max_branch_loading_pct=max_branch_loading_pct,
        max_trafo_loading_pct=max_trafo_loading_pct,
        max_swing_bus_power_mva=max_swing_bus_power_mva,
        branch_rate=branch_rate,
        trafo_rate=trafo_rate,
    )
    violations: Violations = Violations.NO_VIOLATIONS
    for branch in contingency_scenario.branches:
        if branch.is_enabled():
            with disable_branch(branch):
                violations |= check_violations(
                    **dataclasses.asdict(contingency_limits),
                    use_full_newton_raphson=use_full_newton_raphson,
                )
                if violations != Violations.NO_VIOLATIONS:
                    return LimitingFactor(violations, branch)
    for trafo in contingency_scenario.trafos:
        if trafo.is_enabled():
            with disable_trafo(trafo):
                violations |= check_violations(
                    **dataclasses.asdict(contingency_limits),
                    use_full_newton_raphson=use_full_newton_raphson,
                )
                if violations != Violations.NO_VIOLATIONS:
                    return LimitingFactor(violations, trafo)
    return LimitingFactor(violations, None)


def get_default_contingency_limits() -> ViolationsLimits:
    if not all(
        get_contingency_limiting_factor.__annotations__[var_name] == var_type
        for var_name, var_type in ViolationsLimits.__annotations__.items()
    ):
        raise RuntimeError(
            f"{ViolationsLimits.__annotations__=} are different from corresponding "
            f"{get_contingency_limiting_factor.__annotations__=}"
        )
    if (
        contingency_limiting_factor_defaults := get_contingency_limiting_factor.__defaults__
    ) is None:
        raise RuntimeError(f"No defaults for `get_contingency_limiting_factor()`")
    violation_limits_count: int = len(ViolationsLimits.__annotations__)
    return ViolationsLimits(
        *contingency_limiting_factor_defaults[:violation_limits_count]
    )


def get_contingency_scenario(
    use_full_newton_raphson: bool,
    solver_opts: dict,
    contingency_limits: Optional[ViolationsLimits] = get_default_contingency_limits(),
) -> ContingencyScenario:
    contingency_limits = contingency_limits or get_default_contingency_limits()

    def check_contingency_limits_violations() -> Violations:
        return check_violations(
            **dataclasses.asdict(contingency_limits),
            use_full_newton_raphson=use_full_newton_raphson,
            solver_opts=solver_opts,
        )

    def branch_is_not_critical(
        branch: Branch,
    ) -> bool:
        if branch.is_enabled():
            with disable_branch(branch) as is_disabled:
                if is_disabled:
                    violations: Violations = check_contingency_limits_violations()
                    return violations == Violations.NO_VIOLATIONS
        return False

    def trafo_is_not_critical(
        trafo: Trafo,
    ) -> bool:
        if trafo.is_enabled():
            with disable_trafo(trafo) as is_disabled:
                if is_disabled:
                    violations: Violations = check_contingency_limits_violations()
                    return violations == Violations.NO_VIOLATIONS
        return False

    not_critical_branches: tuple[Branch, ...] = tuple(
        branch for branch in Branches() if branch_is_not_critical(branch)
    )
    not_critical_trafos: tuple[Trafo, ...] = tuple(
        trafo for trafo in Trafos() if trafo_is_not_critical(trafo)
    )
    return ContingencyScenario(not_critical_branches, not_critical_trafos)
