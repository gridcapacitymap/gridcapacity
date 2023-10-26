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
import sys
import unittest

from gridcapacity import ViolationsStats
from gridcapacity.backends import wrapped_funcs as wf
from gridcapacity.backends.subsystems.branch import Branch
from gridcapacity.backends.subsystems.trafo import Trafo
from gridcapacity.contingency_analysis import (
    ContingencyScenario,
    LimitingFactor,
    get_contingency_limiting_factor,
    get_contingency_scenario,
    get_default_contingency_limits,
)
from gridcapacity.envs import envs
from gridcapacity.violations_analysis import Violations, ViolationsLimits
from tests import DEFAULT_CASE

if sys.platform == "win32" and not envs.pandapower_backend:
    from gridcapacity.backends.psse import init_psse


class TestContingencyAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if sys.platform == "win32" and not envs.pandapower_backend:
            init_psse()
        wf.open_case(DEFAULT_CASE)
        ViolationsStats.reset_base_case_violations()

    def test_get_contingency_limiting_factor(self) -> None:
        branch_arg = (
            (154, 205)
            if sys.platform == "win32" and not envs.pandapower_backend
            else (5, 10)
        )
        if sys.platform == "win32" and not envs.pandapower_backend:
            self.assertEqual(
                LimitingFactor(
                    Violations.BRANCH_LOADING | Violations.BUS_UNDERVOLTAGE,
                    ss=Branch(*branch_arg),
                ),
                get_contingency_limiting_factor(
                    ContingencyScenario(branches=(Branch(*branch_arg),), trafos=()),
                ),
            )
        else:
            self.assertEqual(
                LimitingFactor(
                    Violations.TRAFO_LOADING
                    | Violations.BRANCH_LOADING
                    | Violations.BUS_UNDERVOLTAGE,
                    ss=Branch(*branch_arg),
                ),
                get_contingency_limiting_factor(
                    ContingencyScenario(branches=(Branch(*branch_arg),), trafos=()),
                ),
            )

    def test_get_default_contingency_limits(self) -> None:
        self.assertEqual(
            ViolationsLimits(
                max_bus_voltage_pu=1.12,
                min_bus_voltage_pu=0.88,
                max_branch_loading_pct=120.0,
                max_trafo_loading_pct=120.0,
                max_swing_bus_power_p_mw=1000.0,
                branch_rate="Rate2",
                trafo_rate="Rate1",
            ),
            get_default_contingency_limits(),
        )

    def test_get_contingency_scenario(self) -> None:
        branch_args = (
            (  # "1 " with space is needed, the default value "1" without space is not working
                (151, 152, "2 "),
                (151, 201, "1 "),
                (152, 202, "1 "),
                (152, 3004, "1 "),
                (153, 154, "1 "),
                (153, 154, "2 "),
                (153, 3006, "1 "),
                (154, 203, "1 "),
                (154, 3008, "1 "),
            )
            if sys.platform == "win32" and not envs.pandapower_backend
            else (
                (2, 6),
                (3, 7),
                (3, 16),
                (4, 5),
                (4, 5),
                (4, 18),
                (5, 8),
                (5, 20),
                (8, 10),
                (8, 10),
                (13, 15),
                (14, 16),
                (15, 17),
                (15, 17),
                (17, 18),
                (17, 20),
                (19, 20),
            )
        )
        if sys.platform == "win32" and not envs.pandapower_backend:
            self.assertEqual(
                ContingencyScenario(
                    branches=tuple(Branch(*args) for args in branch_args),
                    trafos=(),
                ),
                get_contingency_scenario(False, {"options1": 1, "options5": 1}),
            )
        else:
            self.assertEqual(
                ContingencyScenario(
                    tuple(Branch(*args) for args in branch_args),
                    trafos=(
                        Trafo(6, 12),
                        Trafo(14, 13),
                        Trafo(13, 21),
                        Trafo(16, 17),
                        Trafo(20, 22),
                    ),
                ),
                get_contingency_scenario(False, {"options1": 1, "options5": 1}),
            )
