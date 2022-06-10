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
import errno
import functools
import logging
import os
from pathlib import Path
from typing import Final, Optional

import pandapower as pp
from pandapower import LoadflowNotConverged

import gridcapacity.backends.pandapower as pp_backend

log = logging.getLogger(__name__)
LOG_LEVEL: Final[int] = (
    logging.INFO
    if not os.getenv("GRID_CAPACITY_TREAT_VIOLATIONS_AS_WARNINGS")
    else logging.WARNING
)


def is_converged() -> bool:
    return pp_backend.net.get("converged", False)


@functools.cache
def _get_case_path(case_name: str) -> Path:
    probable_case_path: Path = Path(case_name)
    case_path = (
        probable_case_path
        if probable_case_path.is_absolute()
        else Path(__file__).absolute().parents[3] / probable_case_path
    )
    if not case_path.exists():
        raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), str(case_path))
    return case_path


def open_case(case_name: str) -> None:
    case_path: Path = _get_case_path(case_name)
    if case_path.suffix == ".json":
        pp_backend.net = pp.from_json(case_path)
    else:
        raise RuntimeError(
            f"Unsupported file type {case_path.suffix.removeprefix('.')}"
        )
    log.info(f"Opened file '{case_path}'")
    log.info(pp_backend.net)


def run_solver(
    use_full_newton_raphson: bool,
    solver_opts: Optional[dict] = None,
) -> None:
    """Default solver options are empty."""
    effective_solver_opts = solver_opts or dict()
    try:
        if not use_full_newton_raphson:
            pp.runpp(pp_backend.net, **effective_solver_opts)
        else:
            pp.runpp(pp_backend.net, algorithm="fdbx", **effective_solver_opts)
    except LoadflowNotConverged as e:
        log.log(LOG_LEVEL, e.args)
    pp.diagnostic(
        pp_backend.net,
        report_style="compact",
        warnings_only=True,
        return_result_dict=False,
    )
