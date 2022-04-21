import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Union

import psspy

from pssetools import wrapped_funcs as wf
from pssetools.wrapped_funcs import PsseApiCallError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Branch:
    from_number: int
    to_number: int
    branch_id: str

    def is_enabled(self) -> bool:
        """Return `True` if is enabled"""
        status: int = wf.brnint(
            self.from_number, self.to_number, self.branch_id, "STATUS"
        )
        return status != 0


@dataclass
class RawBranches:
    from_number: list[int]
    to_number: list[int]
    branch_id: list[str]


class Branches:
    def __init__(self) -> None:
        self._raw_branches: RawBranches = RawBranches(
            wf.abrnint(string="fromNumber")[0],
            wf.abrnint(string="toNumber")[0],
            wf.abrnchar(string="id")[0],
        )

    def __iter__(self) -> Iterator[Branch]:
        for branch_idx in range(len(self)):
            yield Branch(
                self._raw_branches.from_number[branch_idx],
                self._raw_branches.to_number[branch_idx],
                self._raw_branches.branch_id[branch_idx],
            )

    def __len__(self) -> int:
        return len(self._raw_branches.from_number)


@contextmanager
def disable_branch(branch: Branch) -> Iterator[bool]:
    is_disabled: bool = False
    try:
        error_code: int = psspy.branch_chng_3(
            branch.from_number, branch.to_number, branch.branch_id, st=0
        )
        if error_code == 0:
            is_disabled = True
            yield is_disabled
        else:
            log.info(f"Failed disabling branch {branch=} {error_code=}")
            yield is_disabled
    finally:
        if is_disabled:
            wf.branch_chng_3(
                branch.from_number, branch.to_number, branch.branch_id, st=1
            )


@dataclass(frozen=True)
class Bus:
    number: int
    ex_name: str


@dataclass
class RawBuses:
    number: list[int]
    ex_name: list[str]


class Buses:
    def __init__(self) -> None:
        self._raw_buses: RawBuses = RawBuses(
            wf.abusint(string="number")[0],
            wf.abuschar(string="exName")[0],
        )

    def __iter__(self) -> Iterator[Bus]:
        for bus_idx in range(len(self)):
            yield Bus(
                self._raw_buses.number[bus_idx],
                self._raw_buses.ex_name[bus_idx],
            )

    def __len__(self) -> int:
        return len(self._raw_buses.number)


@dataclass(frozen=True)
class Load:
    number: int
    ex_name: str
    load_id: str
    mva_act: complex


@dataclass(frozen=True)
class RawLoads:
    number: list[int]
    ex_name: list[str]
    load_id: list[str]
    mva_act: list[complex]


class Loads:
    def __init__(self) -> None:
        self._raw_loads: RawLoads = RawLoads(
            wf.aloadint(string="number")[0],
            wf.aloadchar(string="exName")[0],
            wf.aloadchar(string="id")[0],
            wf.aloadcplx(string="mvaAct")[0],
        )

    def __iter__(self) -> Iterator[Load]:
        for load_idx in range(len(self)):
            yield Load(
                self._raw_loads.number[load_idx],
                self._raw_loads.ex_name[load_idx],
                self._raw_loads.load_id[load_idx],
                self._raw_loads.mva_act[load_idx],
            )

    def __len__(self) -> int:
        return len(self._raw_loads.number)


class TemporaryBusLoad:
    TEMP_LOAD_ID: str = "Tm"

    def __init__(self, bus: Bus) -> None:
        self._bus: Bus = bus
        self._context_manager_is_active: bool = False

    def __enter__(self):
        # Create load
        wf.load_data_6(self._bus.number, self.TEMP_LOAD_ID)
        self._context_manager_is_active = True

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Delete load
        wf.purgload(self._bus.number, self.TEMP_LOAD_ID)
        self._context_manager_is_active = False

    def __call__(self, new_load: complex) -> None:
        if not self._context_manager_is_active:
            raise RuntimeError(
                "Load modification without context manager is prohibited. "
                "Use `with TemporaryBusLoad(bus) as temp_load:`."
            )
        wf.load_chng_6(
            self._bus.number, self.TEMP_LOAD_ID, realar=[new_load.real, new_load.imag]
        )


class TemporaryBusMachine:
    TEMP_MACHINE_ID: str = "Tm"

    def __init__(self, bus: Bus) -> None:
        self._bus: Bus = bus
        self._context_manager_is_active: bool = False

    def __enter__(self):
        # Create machine
        wf.machine_data_4(self._bus.number, self.TEMP_MACHINE_ID)
        self._context_manager_is_active = True

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Delete machine
        wf.purgmac(self._bus.number, self.TEMP_MACHINE_ID)
        self._context_manager_is_active = False

    def __call__(self, gen_mva: complex) -> None:
        if not self._context_manager_is_active:
            raise RuntimeError(
                "Machine modification without context manager is prohibited. "
                "Use `with TemporaryBusMachine(bus) as temp_gen:`."
            )
        wf.machine_chng_4(
            self._bus.number, self.TEMP_MACHINE_ID, realar=[gen_mva.real, gen_mva.imag]
        )


TemporaryBusSubsystem = Union[TemporaryBusLoad, TemporaryBusMachine]


@dataclass(frozen=True)
class Trafo:
    from_number: int
    to_number: int
    trafo_id: str

    def is_enabled(self) -> bool:
        """Return `True` if is enabled"""
        # Trafo status is available through the branches `brnint` API only.
        # It isn't available through the trafos `xfrint` API.
        status: int = wf.brnint(
            self.from_number, self.to_number, self.trafo_id, "STATUS"
        )
        return status != 0


@dataclass
class RawTrafos:
    from_number: list[int]
    to_number: list[int]
    trafo_id: list[str]


class Trafos:
    def __init__(self) -> None:
        self._raw_trafos: RawTrafos = RawTrafos(
            wf.atrnint(string="fromNumber")[0],
            wf.atrnint(string="toNumber")[0],
            wf.atrnchar(string="id")[0],
        )

    def __iter__(self) -> Iterator[Trafo]:
        for trafo_idx in range(len(self)):
            yield Trafo(
                self._raw_trafos.from_number[trafo_idx],
                self._raw_trafos.to_number[trafo_idx],
                self._raw_trafos.trafo_id[trafo_idx],
            )

    def __len__(self) -> int:
        return len(self._raw_trafos.from_number)


@contextmanager
def disable_trafo(trafo: Trafo) -> Iterator[bool]:
    is_disabled: bool = False
    try:
        error_code, _ = psspy.two_winding_chng_6(
            trafo.from_number, trafo.to_number, trafo.trafo_id, intgar1=0
        )
        if error_code == 0:
            is_disabled = True
            yield is_disabled
        else:
            log.info(f"Failed disabling trafo {trafo=} {error_code=}")
            yield is_disabled
    finally:
        if is_disabled:
            wf.two_winding_chng_6(
                trafo.from_number, trafo.to_number, trafo.trafo_id, intgar1=1
            )
