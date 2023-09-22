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

from gridcapacity.backends import wrapped_funcs as wf
from gridcapacity.backends.subsystems import Branch
from gridcapacity.envs import envs
from gridcapacity.violations_analysis import (
    Violations,
    ViolationsStats,
    check_violations,
)
from tests import DEFAULT_CASE

if sys.platform == "win32" and not envs.pandapower_backend:
    from gridcapacity.backends.psse import init_psse


class TestViolationsAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if sys.platform == "win32" and not envs.pandapower_backend:
            init_psse()
        ViolationsStats.reset()

    def test_not_converged(self) -> None:
        wf.open_case(DEFAULT_CASE)
        branch_args = (
            (154, 3008)
            if sys.platform == "win32" and not envs.pandapower_backend
            else (5, 20)
        )
        Branch(*branch_args).set_r(10.0)
        self.assertEqual(Violations.NOT_CONVERGED, check_violations())

    def test_bus_overvoltage(self) -> None:
        wf.open_case(DEFAULT_CASE)
        self.assertEqual(
            Violations.BUS_OVERVOLTAGE,
            check_violations(max_trafo_loading_pct=110.0, max_bus_voltage_pu=0.9),
        )
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        else:
            self.assertEqual(
                {
                    0.9: {
                        0: [1.02],
                        1: [1.02],
                        2: [1.0049957623563202],
                        3: [0.9965497100851284],
                        4: [0.9713180191374471],
                        5: [0.906023303993857],
                        6: [1.0270995158997118],
                        7: [0.9867971068362426],
                        8: [0.937484271617664],
                        9: [0.9504205281039497],
                        10: [0.9144496566324744],
                        11: [0.98],
                        12: [1.0400000000000003],
                        13: [1.0245930700977035],
                        14: [1.0201501803428323],
                        15: [1.0153492818760117],
                        16: [0.999455971345114],
                        17: [0.977371597778954],
                        18: [0.973568068955505],
                        19: [0.9430062941853239],
                        20: [0.9353504288240114],
                        21: [1.04],
                        22: [1.02],
                    }
                },
                ViolationsStats.asdict()[Violations.BUS_OVERVOLTAGE],
            )

    def test_bus_undervoltage(self) -> None:
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        else:
            wf.open_case(DEFAULT_CASE)
            self.assertEqual(
                Violations.BUS_UNDERVOLTAGE,
                check_violations(max_trafo_loading_pct=110, min_bus_voltage_pu=1),
            )

    def test_branch_loading(self) -> None:
        wf.open_case(DEFAULT_CASE)
        branch_args = (
            ((152, 3004), (153, 3006))
            if sys.platform == "win32" and not envs.pandapower_backend
            else ((3, 16), (4, 18))
        )
        for args in branch_args:
            branch = Branch(*args)
            branch.disable()
        if sys.platform == "win32" and not envs.pandapower_backend:
            self.assertEqual(
                Violations.BRANCH_LOADING, check_violations(max_trafo_loading_pct=115.0)
            )
            self.assertEqual(
                {100.0: ({4: [115.15924072265625]})},
                ViolationsStats.asdict()[Violations.BRANCH_LOADING],
            )
        else:
            print(ViolationsStats.asdict()[Violations.BRANCH_LOADING])
            self.assertEqual(
                Violations.BRANCH_LOADING,
                check_violations(max_trafo_loading_pct=125.0, min_bus_voltage_pu=0.8),
            )
            self.assertEqual(
                {100.0: ({5: [116.57410137972397]})},
                ViolationsStats.asdict()[Violations.BRANCH_LOADING],
            )

    def test_2w_trafo_loading(self) -> None:
        wf.open_case(DEFAULT_CASE)
        if sys.platform == "win32" and not envs.pandapower_backend:
            self.assertEqual(Violations.TRAFO_LOADING, check_violations())
            self.assertEqual(
                {100.0: {6: [102.952880859375]}},
                ViolationsStats.asdict()[Violations.TRAFO_LOADING],
            )
        else:
            self.assertEqual(Violations.TRAFO_LOADING, check_violations())
            self.assertEqual(
                {100.0: {6: [107.74284564774533]}},
                ViolationsStats.asdict()[Violations.TRAFO_LOADING],
            )

    @unittest.skipIf(envs.pandapower_backend, "No 3w trafo in pandapower")
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
        if sys.platform == "win32" and not envs.pandapower_backend:
            wf.load_data_6(3011, realar1=1000.0)
            self.assertEqual(
                Violations.SWING_BUS_LOADING,
                check_violations(max_trafo_loading_pct=110.0),
            )
            self.assertEqual(
                {1000.0: {0: [1258.0638427734375]}},
                ViolationsStats.asdict()[Violations.SWING_BUS_LOADING],
            )
        else:
            self.assertEqual(
                Violations.SWING_BUS_LOADING,
                check_violations(
                    max_swing_bus_power_p_mw=1.0, max_trafo_loading_pct=110
                ),
            )
            self.assertEqual(
                {1.0: {0: [262.5125194083306]}},
                ViolationsStats.asdict()[Violations.SWING_BUS_LOADING],
            )

    def test_no_violations(self) -> None:
        wf.open_case(DEFAULT_CASE)
        self.assertEqual(
            Violations.NO_VIOLATIONS, check_violations(max_trafo_loading_pct=110.0)
        )


if __name__ == "__main__":
    unittest.main()
