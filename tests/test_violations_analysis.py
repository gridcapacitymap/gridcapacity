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
import unittest

import pssetools
from pssetools import wrapped_funcs as wf
from pssetools.violations_analysis import Violations, check_violations
from tests import DEFAULT_CASE


class TestCheckViolations(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pssetools.init_psse()

    def test_not_converged(self) -> None:
        wf.open_case(DEFAULT_CASE)
        wf.branch_chng_3(154, 3008, realar1=10.0)
        self.assertEqual(Violations.NOT_CONVERGED, check_violations())

    def test_bus_overvoltage(self) -> None:
        wf.open_case(DEFAULT_CASE)
        self.assertEqual(
            Violations.BUS_OVERVOLTAGE,
            check_violations(max_trafo_loading_pct=110.0, max_bus_voltage_pu=0.9),
        )

    def test_bus_undervoltage(self) -> None:
        wf.open_case("iec60909_testnetwork_50Hz.sav")
        self.assertEqual(
            Violations.BUS_UNDERVOLTAGE,
            check_violations(
                use_full_newton_raphson=True, max_trafo_loading_pct=1200.0
            ),
        )

    def test_branch_loading(self) -> None:
        wf.open_case(DEFAULT_CASE)
        wf.branch_chng_3(152, 3004, st=0)
        wf.branch_chng_3(153, 3006, st=0)
        self.assertEqual(
            Violations.BRANCH_LOADING, check_violations(max_trafo_loading_pct=115.0)
        )

    def test_2w_trafo_loading(self) -> None:
        wf.open_case(DEFAULT_CASE)
        self.assertEqual(Violations.TRAFO_LOADING, check_violations())

    def test_3w_trafo_loading(self) -> None:
        wf.open_case("iec60909_testnetwork_50Hz.sav")
        self.assertEqual(
            Violations.TRAFO_3W_LOADING,
            check_violations(
                use_full_newton_raphson=True,
                min_bus_voltage_pu=10e-9,
                max_trafo_loading_pct=1170.0,
            ),
        )

    def test_swing_bus_loading(self) -> None:
        wf.open_case(DEFAULT_CASE)
        wf.load_data_6(3011, realar1=1000.0)
        self.assertEqual(
            Violations.SWING_BUS_LOADING, check_violations(max_trafo_loading_pct=110.0)
        )

    def test_no_violations(self) -> None:
        wf.open_case(DEFAULT_CASE)
        self.assertEqual(
            Violations.NO_VIOLATIONS, check_violations(max_trafo_loading_pct=110.0)
        )


if __name__ == "__main__":
    unittest.main()
