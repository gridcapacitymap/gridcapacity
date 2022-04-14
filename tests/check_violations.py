import unittest

import pssetools
from pssetools import wrapped_funcs as wf
from pssetools.violations_analysis import Violations, check_violations


class CheckViolations(unittest.TestCase):
    def test_default_violation(self):
        pssetools.init_psse()
        wf.open_case("savnw.sav")
        wf.fdns()
        self.assertEqual(check_violations(), Violations.TRAFO_LOADING)


if __name__ == "__main__":
    unittest.main()
