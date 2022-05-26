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
from pssetools.violations_analysis import ViolationsLimits
from tests import DEFAULT_CASE


class TestCheckCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pssetools.init_psse()

    normal_limits: ViolationsLimits = ViolationsLimits(
        max_bus_voltage_pu=1.1,
        min_bus_voltage_pu=0.9,
        max_branch_loading_pct=120.0,
        max_trafo_loading_pct=110.0,
        max_swing_bus_power_mva=1000.0,
    )

    def test_runtime_error(self) -> None:
        with self.assertRaises(RuntimeError):
            buses_headroom(
                case_name=DEFAULT_CASE,
                upper_load_limit_p_mw=100.0,
                upper_gen_limit_p_mw=80.0,
            )

    def test_violated_bus_amount(self) -> None:
        self.assertEqual(
            23,
            len(
                buses_headroom(
                    case_name=DEFAULT_CASE,
                    upper_load_limit_p_mw=100.0,
                    upper_gen_limit_p_mw=80.0,
                    normal_limits=self.normal_limits,
                )
            ),
        )
