import unittest

import pssetools
from pssetools import wrapped_funcs as wf
from pssetools.contingency_analysis import (
    ContingencyScenario,
    LimitingFactor,
    get_contingency_limiting_factor,
    get_contingency_scenario,
    get_default_contingency_limits,
)
from pssetools.subsystems import Branch
from pssetools.violations_analysis import Violations, ViolationsLimits
from tests import DEFAULT_CASE


class TestContingencyAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pssetools.init_psse()
        wf.open_case(DEFAULT_CASE)

    def test_get_contingency_limiting_factor(self) -> None:
        self.assertEqual(
            LimitingFactor(
                Violations.BRANCH_LOADING | Violations.BUS_UNDERVOLTAGE,
                ss=Branch(154, 205),
            ),
            get_contingency_limiting_factor(
                ContingencyScenario(branches=(Branch(154, 205),), trafos=()),
            ),
        )

    def test_get_default_contingency_limits(self) -> None:
        self.assertEqual(
            ViolationsLimits(
                max_bus_voltage_pu=1.12,
                min_bus_voltage_pu=0.88,
                max_branch_loading_pct=120.0,
                max_trafo_loading_pct=120.0,
                max_swing_bus_power_mva=1000.0,
                branch_rate="Rate2",
                trafo_rate="Rate1",
            ),
            get_default_contingency_limits(),
        )

    def test_get_contingency_scenario(self) -> None:
        self.assertEqual(
            ContingencyScenario(
                branches=(  # "1 " with space is needed, the default value "1" without space is not working
                    Branch(151, 152, "2 "),
                    Branch(151, 201, "1 "),
                    Branch(152, 202, "1 "),
                    Branch(152, 3004, "1 "),
                    Branch(153, 154, "1 "),
                    Branch(153, 154, "2 "),
                    Branch(153, 3006, "1 "),
                    Branch(154, 203, "1 "),
                    Branch(154, 3008, "1 "),
                ),
                trafos=(),
            ),
            get_contingency_scenario(False, {"options1": 1, "options5": 1}),
        )
