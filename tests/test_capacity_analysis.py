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

from gridcapacity.backends.subsystems import Bus
from gridcapacity.backends.subsystems.branch import Branch
from gridcapacity.backends.subsystems.trafo import Trafo
from gridcapacity.capacity_analysis import (
    CapacityAnalysisStats,
    Headroom,
    UnfeasibleCondition,
    buses_headroom,
)
from gridcapacity.contingency_analysis import ContingencyScenario, LimitingFactor
from gridcapacity.envs import envs
from gridcapacity.violations_analysis import Violations, ViolationsLimits
from tests import DEFAULT_CASE

if sys.platform == "win32" and not envs.pandapower_backend:
    from gridcapacity.backends.psse import init_psse


class TestCapacityAnalysis(unittest.TestCase):
    headroom: Headroom

    @classmethod
    def setUpClass(cls) -> None:
        if sys.platform == "win32" and not envs.pandapower_backend:
            init_psse()
        branch_args = (
            (
                (151, 201),
                (152, 202),
                (152, 3004),
                (153, 154),
                (153, 3006),
                (154, 203),
                (154, 3008),
            )
            if sys.platform == "win32" and not envs.pandapower_backend
            else (
                (2, 6),
                (3, 7),
                (3, 16),
                (4, 5),
                (4, 18),
                (5, 8),
                (5, 20),
            )
        )
        trafo_args = (
            (
                (3001, 3002),
                (3004, 3005),
            )
            if sys.platform == "win32" and not envs.pandapower_backend
            else ((13, 14), (16, 17))
        )
        cls.headroom = buses_headroom(
            case_name=DEFAULT_CASE,
            upper_load_limit_p_mw=100.0,
            upper_gen_limit_p_mw=80.0,
            normal_limits=ViolationsLimits(
                max_bus_voltage_pu=1.05,
                min_bus_voltage_pu=0.97,
                max_branch_loading_pct=100.0,
                max_trafo_loading_pct=110.0,
                max_swing_bus_power_p_mw=1000.0,
                branch_rate="Rate1",
                trafo_rate="Rate1",
            ),
            contingency_scenario=ContingencyScenario(
                branches=tuple(Branch(*args) for args in branch_args),
                trafos=tuple(Trafo(*args) for args in trafo_args),
            ),
        )

    def test_capacity_analysis_stats(self) -> None:
        self.assertEqual(0, len(CapacityAnalysisStats.contingencies_dict()))
        if sys.platform == "win32" and not envs.pandapower_backend:
            self.assertEqual(21, len(CapacityAnalysisStats.feasibility_dict()))
            self.assertEqual(
                [
                    UnfeasibleCondition(
                        -80 - 38.74576838702821j,
                        LimitingFactor(
                            Violations.BUS_UNDERVOLTAGE | Violations.BUS_OVERVOLTAGE,
                        ),
                    ),
                    UnfeasibleCondition(
                        -15 - 7.264831572567789j,
                        LimitingFactor(
                            Violations.BUS_UNDERVOLTAGE | Violations.BUS_OVERVOLTAGE,
                        ),
                    ),
                ],
                CapacityAnalysisStats.feasibility_dict()[
                    Bus(number=101, ex_name="NUC-A       21.600", type=2)
                ][0:-1:3],
            )
        else:
            self.assertEqual(19, len(CapacityAnalysisStats.feasibility_dict()))
            self.assertEqual(
                [
                    UnfeasibleCondition(
                        -80 - 38.74576838702821j,
                        LimitingFactor(
                            Violations.BUS_UNDERVOLTAGE,
                        ),
                    ),
                    UnfeasibleCondition(
                        -40 - 19.372884193514103j,
                        LimitingFactor(
                            Violations.BUS_UNDERVOLTAGE,
                        ),
                    ),
                ],
                CapacityAnalysisStats.feasibility_dict()[
                    Bus(number=100, ex_name="21.6 77.0", type=1)
                ],
            )

    def test_loads_avail_mva(self) -> None:
        # zero, average and high values
        if sys.platform == "win32" and not envs.pandapower_backend:
            load_avail_mva_values = (
                (5, 0),
                (3, 65.625 + 31.783638129984077j),
                (0, 100 + 48.432210483785255j),
            )
        else:
            load_avail_mva_values = (
                (5, 15.625 + 7.5675328880914465j),
                (3, 18.75 + 9.081039465709736j),
                (0, 100 + 48.432210483785255j),
            )
        for bus_idx, load_avail_mva in load_avail_mva_values:
            with self.subTest(bus_idx=bus_idx, load_avail_mva=load_avail_mva):
                self.assertEqual(load_avail_mva, self.headroom[bus_idx].load_avail_mva)

    def test_gens_avail_mva(self) -> None:
        # zero, average and high values
        if sys.platform == "win32" and not envs.pandapower_backend:
            gen_avail_mva_values = (
                (3, 0),
                (12, 25 + 12.108052620946314j),
                (21, 52.5 + 25.42691050398726j),
            )
        else:
            gen_avail_mva_values = (
                (3, 0),
                (12, 45 + 21.794494717703365j),
                (21, 0j),
            )
        for bus_idx, gen_avail_mva in gen_avail_mva_values:
            with self.subTest(bus_idx=bus_idx, gen_avail_mva=gen_avail_mva):
                self.assertEqual(gen_avail_mva, self.headroom[bus_idx].gen_avail_mva)

    def test_raise_not_converged_base_case(self) -> None:
        # expecting RuntimeError Violations.NOT_CONVERGED
        with self.assertRaises(RuntimeError):
            solver_options = (
                # Flat start and non-divergent solution
                {"options6": 1, "options8": 1}
                if sys.platform == "win32" and not envs.pandapower_backend
                else {"init": "flat", "max_iteration": 1}
            )
            buses_headroom(
                case_name=DEFAULT_CASE,
                upper_load_limit_p_mw=100.0,
                upper_gen_limit_p_mw=80.0,
                solver_opts=solver_options,
            )

    def test_violated_bus_count(self) -> None:
        self.assertEqual(
            23,
            len(self.headroom),
        )
