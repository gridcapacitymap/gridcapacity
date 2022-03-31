from typing import Dict, Final, Tuple

FDNS_RV: Final[Tuple[str, ...]] = (
    "no error occurred",
    "invalid OPTIONS value",
    "generators are converted",
    "buses in island(s) without a swing bus; use activity TREE",
    "bus type code and series element status inconsistencies",
    "prerequisite requirements for API are not met",
)

READ_RV: Final[Dict[int, str]] = {
    0: "no error occurred",
    1: "invalid NUMNAM value",
    2: "invalid revision number",
    3: "unable to convert file",
    4: "error opening temporary file",
    10: "error opening IFILE",
    11: "prerequisite requirements for API are not met",
}

SOLVED_RV: Final[Tuple[str, ...]] = (
    "Met convergence tolerance",
    "Iteration limit exceeded",
    "Blown up (only when non-divergent option disabled)",
    "Terminated by non-divergent option",
    "Terminated by console interrupt",
    "Singular Jacobian matrix or voltage of 0.0 de- tected",
    "Inertial power flow dispatch error (INLF)",
    "OPF solution met convergence tolerance (NOPF)",
    "Solution not attempted",
    "RSOL converged with Phase shift locked",
    "RSOL converged with TOLN increased",
    "RSOL converged with Y load conversion due to low voltage",
)
