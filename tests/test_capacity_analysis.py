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
from pssetools.capacity_analysis import buses_headroom
from pssetools.contingency_analysis import ContingencyScenario
from pssetools.subsystems import Branch, Trafo
from pssetools.violations_analysis import ViolationsLimits
from tests import DEFAULT_CASE


class TestCheckCapacity(unittest.TestCase):
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
                        [151, 201],
                        [152, 202],
                        [152, 3004],
                        [153, 154],
                        [153, 3006],
                        [154, 203],
                        [154, 3008],
                    )
                ),
                trafos=(Trafo(3001, 3002), Trafo(3004, 3005)),
            ),
        )

    loads = [0, 65.625 + 31.783638129984077j, 100 + 48.432210483785255j]
    gens = [0, 25 + 12.108052620946314j, 52.5 + 25.42691050398726j]

    def test_load_average(self) -> None:
        self.assertEqual(self.loads[1], self.headroom[3].load_avail_mva)

    def test_load_high(self) -> None:
        self.assertEqual(self.loads[2], self.headroom[0].load_avail_mva)

    def test_load_zero(self) -> None:
        self.assertEqual(self.loads[0], self.headroom[5].load_avail_mva)

    def test_gen_average(self) -> None:
        self.assertEqual(self.gens[1], self.headroom[12].gen_avail_mva)

    def test_gen_high(self) -> None:
        self.assertEqual(self.gens[2], self.headroom[21].gen_avail_mva)

    def test_gen_zero(self) -> None:
        self.assertEqual(self.gens[0], self.headroom[3].gen_avail_mva)

    def test_runtime_error(self) -> None:
        with self.assertRaises(
            RuntimeError
        ):  # expecting RuntimeError Violations.TRAFO_LOADING
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
