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
        self.assertEqual(Violations.NOT_CONVERGED, check_violations())

    def test_bus_overvoltage(self):
        wf.open_case("savnw.sav")
        self.assertEqual(
            Violations.BUS_OVERVOLTAGE,
            check_violations(max_trafo_loading_pct=110.0, max_bus_voltage_pu=0.9),
        )

    def test_bus_undervoltage(self):
        wf.open_case("iec60909_testnetwork_50Hz.sav")
        self.assertEqual(
            Violations.BUS_UNDERVOLTAGE,
            check_violations(
                use_full_newton_raphson=True, max_trafo_loading_pct=1200.0
            ),
        )

    def test_branch_loading(self):
        wf.open_case("savnw.sav")
        wf.branch_chng_3(152, 3004, "1", st=0)
        wf.branch_chng_3(153, 3006, "1", st=0)
        self.assertEqual(
            Violations.BRANCH_LOADING,
            check_violations(max_trafo_loading_pct=115.0, max_branch_loading_pct=115.0),
        )

    def test_2w_trafo_loading(self):
        wf.open_case("savnw.sav")
        self.assertEqual(Violations.TRAFO_LOADING, check_violations())

    def test_swing_bus_loading(self):
        wf.open_case("savnw.sav")
        wf.load_data_6(3011, "1", realar1=1000.0)
        self.assertEqual(
            Violations.SWING_BUS_LOADING, check_violations(max_trafo_loading_pct=110.0)
        )

    def test_no_violations(self):
        wf.open_case("savnw.sav")
        self.assertEqual(
            Violations.NO_VIOLATIONS, check_violations(max_trafo_loading_pct=110)
        )


if __name__ == "__main__":
    unittest.main()
