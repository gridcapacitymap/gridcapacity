import unittest

import pssetools
from pssetools import wrapped_funcs as wf
from pssetools.violations_analysis import Violations, check_violations


class CheckViolations(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pssetools.init_psse()

    def test_not_converged(self):
        wf.open_case("savnw.sav")
        wf.branch_chng_3(154, 3008, "1", realar1=10.0)
        self.assertEqual(check_violations(), Violations.NOT_CONVERGED)

    def test_bus_overvoltage(self):
        wf.open_case("savnw.sav")
        self.assertEqual(
            check_violations(max_trafo_loading_pct=110.0, max_bus_voltage_pu=0.9),
            Violations.BUS_OVERVOLTAGE,
        )

    def test_bus_undervoltage(self):
        wf.open_case("savnw.sav")
        wf.branch_chng_3(152, 3004, "1", st=0)
        wf.branch_chng_3(153, 3006, "1", st=0)
        self.assertEqual(
            check_violations(max_trafo_loading_pct=115.0, max_branch_loading_pct=115.0),
            Violations.BUS_UNDERVOLTAGE,
        )

    def test_branch_loading(self):
        wf.open_case("savnw.sav")
        wf.load_chng_6(205, "1", realar1=900.0, realar2=500.0)
        self.assertEqual(check_violations(), Violations.BRANCH_LOADING)

    def test_trafo_loading(self):
        wf.open_case("savnw.sav")
        self.assertEqual(check_violations(), Violations.TRAFO_LOADING)

    def test_swing_bus_loading(self):
        wf.open_case("savnw.sav")
        wf.load_data_6(3011, "1", realar1=1000.0)
        self.assertEqual(
            check_violations(max_trafo_loading_pct=110.0),
            Violations.SWING_BUS_LOADING,
        )

    def test_no_violations(self):
        wf.open_case("savnw.sav")
        self.assertEqual(
            Violations.NO_VIOLATIONS, check_violations(max_trafo_loading_pct=110)
        )


if __name__ == "__main__":
    unittest.main()
