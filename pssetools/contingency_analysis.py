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
    contingency_limits: Optional[ViolationsLimits] = ViolationsLimits(
        max_bus_voltage_pu=1.12,
        min_bus_voltage_pu=0.88,
        max_branch_loading_pct=120.0,
        max_trafo_loading_pct=120.0,
        max_swing_bus_power_mva=1000.0,
        branch_rate="Rate2",
        trafo_rate="Rate1",
    ),
    use_full_newton_raphson: bool = False,
) -> LimitingFactor:
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
    if (
        tuple(get_contingency_limiting_factor.__annotations__.keys())[1]
        != "contingency_limits"
    ):
        raise RuntimeError(
            f"`get_contingency_limiting_factor()` 2-nd arg should be `contingency_limits`"
        )
    if (
        contingency_limiting_factor_defaults := get_contingency_limiting_factor.__defaults__
    ) is None:
        raise RuntimeError(f"No defaults for `get_contingency_limiting_factor()`")
    # The first `get_contingency_limiting_factor()` argument, `contingency_scenario`,
    # doesn't have a default value,
    # so the `defaults[0]` are defaults for the second argument.
    return contingency_limiting_factor_defaults[0]


def get_contingency_scenario(
    use_full_newton_raphson: bool,
    solver_opts: Optional[dict],
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
