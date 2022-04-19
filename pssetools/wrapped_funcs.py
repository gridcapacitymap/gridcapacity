import errno
import logging
import os
from functools import wraps
from pathlib import Path
from typing import Callable, Final, Optional

import psspy

log = logging.getLogger(__name__)


def process_psse_api_error_code(func: Callable) -> Callable:
    """An exception describing the error that is raised if PSSE API returns non-zero error code"""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Optional[list]:
        api_name: str = func.__name__
        api_func: Callable = getattr(psspy, api_name)
        api_return_value = api_func(*args, **kwargs)
        error_code: int
        return_value: Optional[list] = None
        if isinstance(api_return_value, int):
            error_code = api_return_value
        elif (
            isinstance(api_return_value, tuple)
            and len(api_return_value) == 2
            and isinstance(api_return_value[0], int)
        ):
            error_code = api_return_value[0]
            return_value = api_return_value[1]
        else:
            raise RuntimeError(f"Unknown return value from {api_name=}")
        if error_code != 0:
            api_error_messages: Final[
                Optional[dict[int, str]]
            ] = error_messages_by_api.get(api_name)
            unknown_error_code_message: Final[str] = "See the API user guide"
            error_message: Final[str] = (
                api_error_messages.get(error_code, unknown_error_code_message)
                if api_error_messages is not None
                else unknown_error_code_message
            )
            raise PsseApiCallError(
                f"Failed running {api_name=}: {error_message} ({error_code=})"
            )
        return return_value

    return wrapper


@process_psse_api_error_code
def abrnchar() -> list[list[str]]:
    pass


@process_psse_api_error_code
def abrncplx() -> list[list[complex]]:
    pass


@process_psse_api_error_code
def abrnint() -> list[list[int]]:
    pass


@process_psse_api_error_code
def abrnreal() -> list[list[float]]:
    pass


@process_psse_api_error_code
def abrntypes() -> list[list[str]]:
    pass


@process_psse_api_error_code
def abuschar() -> list[list[str]]:
    pass


@process_psse_api_error_code
def abuscplx() -> list[list[complex]]:
    pass


@process_psse_api_error_code
def abusint() -> list[list[int]]:
    pass


@process_psse_api_error_code
def abusreal() -> list[list[float]]:
    pass


@process_psse_api_error_code
def abustypes() -> list[list[str]]:
    pass


@process_psse_api_error_code
def agenbuschar() -> list[list[str]]:
    pass


@process_psse_api_error_code
def agenbuscplx() -> list[list[complex]]:
    pass


@process_psse_api_error_code
def agenbusint() -> list[list[int]]:
    pass


@process_psse_api_error_code
def agenbusreal() -> list[list[float]]:
    pass


@process_psse_api_error_code
def agenbustypes() -> list[list[str]]:
    pass


@process_psse_api_error_code
def alert_output() -> None:
    pass


@process_psse_api_error_code
def aloadchar() -> list[list[str]]:
    pass


@process_psse_api_error_code
def aloadcplx() -> list[list[complex]]:
    pass


@process_psse_api_error_code
def aloadint() -> list[list[int]]:
    pass


@process_psse_api_error_code
def aloadreal() -> list[list[float]]:
    pass


@process_psse_api_error_code
def aloadtypes() -> list[list[str]]:
    pass


@process_psse_api_error_code
def atrnchar() -> list[list[str]]:
    pass


@process_psse_api_error_code
def atrncplx() -> list[list[complex]]:
    pass


@process_psse_api_error_code
def atrnint() -> list[list[int]]:
    pass


@process_psse_api_error_code
def atrnreal() -> list[list[float]]:
    pass


@process_psse_api_error_code
def atrntypes() -> list[list[str]]:
    pass


@process_psse_api_error_code
def awndchar() -> list[list[str]]:
    pass


@process_psse_api_error_code
def awndcplx() -> list[list[complex]]:
    pass


@process_psse_api_error_code
def awndint() -> list[list[int]]:
    pass


@process_psse_api_error_code
def awndreal() -> list[list[float]]:
    pass


@process_psse_api_error_code
def awndtypes() -> list[list[str]]:
    pass


@process_psse_api_error_code
def branch_chng_3() -> None:
    pass


@process_psse_api_error_code
def brnint() -> int:
    pass


@process_psse_api_error_code
def case() -> None:
    pass


@process_psse_api_error_code
def fdns() -> None:
    pass


@process_psse_api_error_code
def fnsl() -> None:
    pass


@process_psse_api_error_code
def load_data_6() -> None:
    pass


@process_psse_api_error_code
def load_chng_6() -> None:
    pass


@process_psse_api_error_code
def progress_output() -> None:
    pass


@process_psse_api_error_code
def prompt_output() -> None:
    pass


@process_psse_api_error_code
def purgload() -> None:
    pass


@process_psse_api_error_code
def rate_2() -> None:
    pass


@process_psse_api_error_code
def read() -> None:
    pass


@process_psse_api_error_code
def report_output() -> None:
    pass


@process_psse_api_error_code
def rsol() -> None:
    pass


@process_psse_api_error_code
def solved() -> None:
    pass


def is_solved() -> bool:
    try:
        solved()
    except PsseApiCallError:
        return False
    return True


@process_psse_api_error_code
def two_winding_chng_6() -> None:
    pass


class PsseApiCallError(Exception):
    """The PSSE API call returned an error code"""


error_messages_by_api: Final[dict[str, dict[int, str]]] = {
    "abrnchar": {
        0: "No error",
        1: "Working ca is empty",
        2: "In SID value",
        3: "In OWNER value",
        4: "In TIES value",
        5: "In FLAG value",
        6: "In ENTRY value",
        7: "In NSTR value",
        8: "DIM, and hence the size of CARRAY, is no large enough",
        9: "In STRING value",
    },
    "fdns": {
        0: "no error occurred",
        1: "invalid OPTIONS value",
        2: "generators are converted",
        3: "buses in island(s) without a swing bus; use activity TREE",
        4: "bus type code and series element status inconsistencies",
        5: "prerequisite requirements for API are not met",
    },
    "read": {
        0: "no error occurred",
        1: "invalid NUMNAM value",
        2: "invalid revision number",
        3: "unable to convert file",
        4: "error opening temporary file",
        10: "error opening IFILE",
        11: "prerequisite requirements for API are not met",
    },
    "solved": {
        0: "Met convergence tolerance",
        1: "Iteration limit exceeded",
        2: "Blown up (only when non-divergent option disabled)",
        3: "Terminated by non-divergent option",
        4: "Terminated by console interrupt",
        5: "Singular Jacobian matrix or voltage of 0.0 de- tected",
        6: "Inertial power flow dispatch error (INLF)",
        7: "OPF solution met convergence tolerance (NOPF)",
        8: "Solution not attempted",
        9: "RSOL converged with Phase shift locked",
        10: "RSOL converged with TOLN increased",
        11: "RSOL converged with Y load conversion due to low voltage",
    },
}


def _get_case_path(case_name):
    probable_case_path = Path(case_name)
    case_path = case_path = (
        probable_case_path
        if probable_case_path.is_absolute()
        else _get_example_case_path(probable_case_path)
    )
    if not case_path.exists():
        raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), str(case_path))
    return case_path


def _get_example_case_path(case_path):
    """Get example case filepath from the case filename.

    The `EXAMPLE` directory is retrieved based on the current `psspy` module location."""
    psspy_path = Path(psspy.__file__)
    psse_path = psspy_path.parents[1]
    examples_path = psse_path / "EXAMPLE"
    case_path = examples_path / case_path
    return case_path


def open_case(case_name: str):
    case_path = _get_case_path(case_name)
    if case_path.suffix == ".sav":
        case(str(case_path))
    elif case_path.suffix == ".raw":
        read(0, str(case_path))
    log.info(f"Opened file '{case_path}'")
