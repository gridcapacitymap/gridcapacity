"""
Copyright 2023 Vattenfall AB

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

from gridcapacity.utils import p_to_mva


class TestCapacityAnalysisUtils(unittest.TestCase):
    def test_p_to_mva(self) -> None:
        self.assertEqual(1.0, p_to_mva(1.0, 1.0))
        self.assertEqual(1 + 4.898979485566358j, p_to_mva(1.0, 0.2))
        # https://www.electronics-tutorials.ws/accircuits/power-triangle.html
        self.assertEqual(79 + 127.63370190288087j, p_to_mva(79.0, 0.5263))
