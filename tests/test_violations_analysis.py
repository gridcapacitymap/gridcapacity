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

assert sys.platform == "win32"

import pssetools
from pssetools import wrapped_funcs as wf
from pssetools.violations_analysis import Violations, ViolationsStats, check_violations
from tests import DEFAULT_CASE


class TestViolationsAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pssetools.init_psse()
        ViolationsStats.reset()

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
        self.assertEqual(
            {
                0.9: {
                    0: [1.0199999809265137],
                    1: [1.0199999809265137],
                    2: [1.0108561515808105],
                    3: [1.0110337734222412],
                    4: [1.0435134172439575],
                    5: [0.9718165993690491],
                    6: [1.0399999618530273],
                    7: [1.0116071701049805],
                    8: [0.9850585460662842],
                    9: [0.9711413979530334],
                    10: [0.9800000190734863],
                    11: [1.0466423034667969],
                    12: [1.0448108911514282],
                    13: [1.0349271297454834],
                    14: [1.034232497215271],
                    15: [1.031920075416565],
                    16: [1.0270209312438965],
                    17: [1.015120029449463],
                    18: [1.0359790325164795],
                    19: [0.9880131483078003],
                    20: [0.986092746257782],
                    21: [1.0399999618530273],
                    22: [1.0478585958480835],
                }
            },
            ViolationsStats.asdict()[Violations.BUS_OVERVOLTAGE],
        )

    def test_bus_undervoltage(self) -> None:
        wf.open_case("iec60909_testnetwork_50Hz.sav")
        self.assertEqual(
            Violations.BUS_UNDERVOLTAGE,
            check_violations(
                use_full_newton_raphson=True, max_trafo_loading_pct=1200.0
            ),
        )
        self.assertEqual(
            {
                0.9: {
                    2: [0.6334197521209717],
                    3: [0.5146950483322144],
                    7: [3.2308236086464603e-08],
                    10: [3.2308236086464603e-08],
                }
            },
            ViolationsStats.asdict()[Violations.BUS_UNDERVOLTAGE],
        )

    def test_branch_loading(self) -> None:
        wf.open_case(DEFAULT_CASE)
        wf.branch_chng_3(152, 3004, st=0)
        wf.branch_chng_3(153, 3006, st=0)
        self.assertEqual(
            Violations.BRANCH_LOADING, check_violations(max_trafo_loading_pct=115.0)
        )
        self.assertEqual(
            {100.0: ({4: [115.15924072265625]})},
            ViolationsStats.asdict()[Violations.BRANCH_LOADING],
        )

    def test_2w_trafo_loading(self) -> None:
        wf.open_case(DEFAULT_CASE)
        self.assertEqual(Violations.TRAFO_LOADING, check_violations())
        self.assertEqual(
            {100.0: {6: [102.952880859375]}},
            ViolationsStats.asdict()[Violations.TRAFO_LOADING],
        )

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
        self.assertEqual(
            {1170.0: {4: [1195.140625], 5: [1195.140625]}},
            ViolationsStats.asdict()[Violations.TRAFO_3W_LOADING],
        )

    def test_swing_bus_loading(self) -> None:
        wf.open_case(DEFAULT_CASE)
        wf.load_data_6(3011, realar1=1000.0)
        self.assertEqual(
            Violations.SWING_BUS_LOADING, check_violations(max_trafo_loading_pct=110.0)
        )
        self.assertEqual(
            {1000.0: {0: [1259.0836181640625]}},
            ViolationsStats.asdict()[Violations.SWING_BUS_LOADING],
        )

    def test_no_violations(self) -> None:
        wf.open_case(DEFAULT_CASE)
        self.assertEqual(
            Violations.NO_VIOLATIONS, check_violations(max_trafo_loading_pct=110.0)
        )


if __name__ == "__main__":
    unittest.main()
