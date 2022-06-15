import unittest

import pssetools
import pssetools.contingency_analysis
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
    contingency_limits: ViolationsLimits
    contingency_scenario: ContingencyScenario

    @classmethod
    def setUpClass(cls) -> None:
        pssetools.init_psse()
        wf.open_case(DEFAULT_CASE)
        cls.contingency_limits = ViolationsLimits(
            max_bus_voltage_pu=1.12,
            min_bus_voltage_pu=0.88,
            max_branch_loading_pct=120.0,
            max_trafo_loading_pct=120.0,
            max_swing_bus_power_mva=1000.0,
            branch_rate="Rate2",
            trafo_rate="Rate1",
        )
        cls.contingency_scenario = ContingencyScenario(
            branches=(
                Branch(from_number=151, to_number=152, branch_id="2 "),
                Branch(from_number=151, to_number=201, branch_id="1 "),
                Branch(from_number=152, to_number=202, branch_id="1 "),
                Branch(from_number=152, to_number=3004, branch_id="1 "),
                Branch(from_number=153, to_number=154, branch_id="1 "),
                Branch(from_number=153, to_number=154, branch_id="2 "),
                Branch(from_number=153, to_number=3006, branch_id="1 "),
                Branch(from_number=154, to_number=203, branch_id="1 "),
                Branch(from_number=154, to_number=3008, branch_id="1 "),
            ),
            trafos=(),
        )

    def test_get_contingency_limiting_factor(self) -> None:
        self.assertEqual(
            LimitingFactor(
                Violations.BRANCH_LOADING | Violations.BUS_UNDERVOLTAGE,
                ss=Branch(from_number=154, to_number=205, branch_id="1"),
            ),
            get_contingency_limiting_factor(
                ContingencyScenario(branches=(Branch(154, 205),), trafos=()),
            ),
        )

    def test_get_default_contingency_limits(self) -> None:
        self.assertEqual(self.contingency_limits, get_default_contingency_limits())

    def test_get_contingency_scenario(self) -> None:
        self.assertEqual(
            self.contingency_scenario,
            get_contingency_scenario(False, {"options1": 1, "options5": 1}),
        )
