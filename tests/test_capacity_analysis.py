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
from gridcapacity.violations_analysis import ViolationsLimits
from pssetools.capacity_analysis import (
    CapacityAnalysisStats,
    Headroom,
    UnfeasibleCondition,
    buses_headroom,
)
from pssetools.contingency_analysis import ContingencyScenario, LimitingFactor
from pssetools.subsystems import Branch, Bus, Trafo
from tests import DEFAULT_CASE


class TestCapacityAnalysis(unittest.TestCase):
    headroom: Headroom

    @classmethod
    def setUpClass(cls) -> None:
        pssetools.init_psse()
        cls.headroom = buses_headroom(
            case_name=DEFAULT_CASE,
            upper_load_limit_p_mw=100.0,
            upper_gen_limit_p_mw=80.0,
            normal_limits=ViolationsLimits(
                max_bus_voltage_pu=1.05,
                min_bus_voltage_pu=0.97,
                max_branch_loading_pct=100.0,
                max_trafo_loading_pct=110.0,
                max_swing_bus_power_mva=1000.0,
                branch_rate="Rate1",
                trafo_rate="Rate1",
            ),
            contingency_scenario=ContingencyScenario(
                branches=tuple(
                    Branch(*args)
                    for args in (
                        (151, 201),
                        (152, 202),
                        (152, 3004),
                        (153, 154),
                        (153, 3006),
                        (154, 203),
                        (154, 3008),
                    )
                ),
                trafos=(Trafo(3001, 3002), Trafo(3004, 3005)),
            ),
        )

    def test_capacity_analysis_stats(self) -> None:
        self.assertEqual(0, len(CapacityAnalysisStats.contingencies_dict()))
        self.assertEqual(21, len(CapacityAnalysisStats.feasibility_dict()))
        self.assertEqual(
            [
                UnfeasibleCondition(
                    -80 - 38.74576838702821j,
                    LimitingFactor(
                        Violations.BUS_UNDERVOLTAGE | Violations.BUS_OVERVOLTAGE,
                        ss=None,
                    ),
                ),
                UnfeasibleCondition(
                    -15 - 7.264831572567789j,
                    LimitingFactor(
                        Violations.BUS_UNDERVOLTAGE | Violations.BUS_OVERVOLTAGE,
                        ss=None,
                    ),
                ),
            ],
            CapacityAnalysisStats.feasibility_dict()[
                Bus(number=101, ex_name="NUC-A       21.600", type=2)
            ][0:-1:3],
        )

    def test_loads_avail_mva(self) -> None:
        # pairs of bus indexes with zero, average and high load_avail_mva values
        for (bus_idx, load_avail_mva,) in (
            (5, 0),
            (3, 65.625 + 31.783638129984077j),
            (0, 100 + 48.432210483785255j),
        ):
            with self.subTest(bus_idx=bus_idx, load_avail_mva=load_avail_mva):
                self.assertEqual(load_avail_mva, self.headroom[bus_idx].load_avail_mva)

    def test_gens_avail_mva(self) -> None:
        # pairs of bus indexes with zero, average and high gen_avail_mva values
        for (bus_idx, gen_avail_mva,) in (
            (3, 0),
            (12, 25 + 12.108052620946314j),
            (21, 52.5 + 25.42691050398726j),
        ):
            with self.subTest(bus_idx=bus_idx, gen_avail_mva=gen_avail_mva):
                self.assertEqual(gen_avail_mva, self.headroom[bus_idx].gen_avail_mva)

    def test_runtime_error(self) -> None:
        # expecting RuntimeError Violations.TRAFO_LOADING
        with self.assertRaises(RuntimeError):
            buses_headroom(
                case_name=DEFAULT_CASE,
                upper_load_limit_p_mw=100.0,
                upper_gen_limit_p_mw=80.0,
            )

    def test_violated_bus_count(self) -> None:
        self.assertEqual(
            23,
            len(self.headroom),
        )
