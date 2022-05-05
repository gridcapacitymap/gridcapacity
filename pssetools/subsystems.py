import dataclasses
import logging
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from types import TracebackType
from typing import Iterator, Optional, Type, Union, overload

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
    pct_rate1: list[float]


class Branches(Sequence):
    def __init__(self) -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._raw_branches: RawBranches = RawBranches(
            wf.abrnint(string="fromNumber")[0],
            wf.abrnint(string="toNumber")[0],
            wf.abrnchar(string="id")[0],
            wf.abrnreal(string="pctRate1")[0],
        )

    @overload
    def __getitem__(self, idx: int) -> Branch:
        ...

    @overload
    def __getitem__(self, idx: slice) -> tuple[Branch, ...]:
        ...

    def __getitem__(self, idx: Union[int, slice]) -> Union[Branch, tuple[Branch, ...]]:
        if isinstance(idx, int):
            return Branch(
                self._raw_branches.from_number[idx],
                self._raw_branches.to_number[idx],
                self._raw_branches.branch_id[idx],
            )
        elif isinstance(idx, slice):
            return tuple(
                Branch(*args)
                for args in zip(
                    self._raw_branches.from_number[idx],
                    self._raw_branches.to_number[idx],
                    self._raw_branches.branch_id[idx],
                )
            )

    def __len__(self) -> int:
        return len(self._raw_branches.from_number)

    def get_overloaded_indexes(self, max_branch_loading_pct: float) -> tuple[int, ...]:
        return tuple(
            branch_id
            for branch_id, pct_rate1 in enumerate(self._raw_branches.pct_rate1)
            if pct_rate1 > max_branch_loading_pct
        )

    def get_loading_pct(
        self,
        selected_indexes: tuple[int, ...],
    ) -> tuple[float, ...]:
        return tuple(self._raw_branches.pct_rate1[idx] for idx in selected_indexes)

    def log(
        self,
        level: int,
        selected_indexes: Optional[tuple[int, ...]] = None,
    ) -> None:
        if not log.isEnabledFor(level):
            return
        branch_fields: tuple[str, ...] = tuple(
            (*dataclasses.asdict(self[0]).keys(), "pctRate1")
        )
        self._log.log(level, branch_fields)
        for idx, branch in enumerate(self):
            if selected_indexes is None or idx in selected_indexes:
                self._log.log(
                    level,
                    tuple(
                        (
                            *dataclasses.astuple(branch),
                            self._raw_branches.pct_rate1[idx],
                        )
                    ),
                )
        self._log.log(level, branch_fields)


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
    type: int


@dataclass
class RawBuses:
    number: list[int]
    ex_name: list[str]
    type: list[int]
    pu: list[float]


class Buses(Sequence):
    def __init__(self) -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._raw_buses: RawBuses = RawBuses(
            wf.abusint(string="number")[0],
            wf.abuschar(string="exName")[0],
            wf.abusint(string="type")[0],
            wf.abusreal(string="pu")[0],
        )

    @overload
    def __getitem__(self, idx: int) -> Bus:
        ...

    @overload
    def __getitem__(self, idx: slice) -> tuple[Bus, ...]:
        ...

    def __getitem__(self, idx: Union[int, slice]) -> Union[Bus, tuple[Bus, ...]]:
        if isinstance(idx, int):
            return Bus(
                self._raw_buses.number[idx],
                self._raw_buses.ex_name[idx],
                self._raw_buses.type[idx],
            )
        elif isinstance(idx, slice):
            return tuple(
                Bus(*args)
                for args in zip(
                    self._raw_buses.number[idx],
                    self._raw_buses.ex_name[idx],
                    self._raw_buses.type[idx],
                )
            )

    def __len__(self) -> int:
        return len(self._raw_buses.number)

    def get_overvoltage_indexes(self, max_bus_voltage: float) -> tuple[int, ...]:
        return tuple(
            bus_id
            for bus_id, pu_voltage in enumerate(self._raw_buses.pu)
            if pu_voltage > max_bus_voltage
        )

    def get_undervoltage_indexes(self, min_bus_voltage: float) -> tuple[int, ...]:
        return tuple(
            bus_id
            for bus_id, pu_voltage in enumerate(self._raw_buses.pu)
            if pu_voltage < min_bus_voltage
        )

    def get_voltage_pu(
        self,
        selected_indexes: tuple[int, ...],
    ) -> tuple[float, ...]:
        return tuple(self._raw_buses.pu[idx] for idx in selected_indexes)

    def log(
        self,
        level: int,
        selected_indexes: Optional[tuple[int, ...]] = None,
    ) -> None:
        if not log.isEnabledFor(level):
            return
        bus_fields: tuple[str, ...] = tuple((*dataclasses.asdict(self[0]).keys(), "pu"))
        self._log.log(level, bus_fields)
        for idx, bus in enumerate(self):
            if selected_indexes is None or idx in selected_indexes:
                self._log.log(
                    level,
                    tuple((*dataclasses.astuple(bus), self._raw_buses.pu[idx])),
                )
        self._log.log(level, bus_fields)


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


@dataclass(frozen=True)
class Machine:
    number: int
    ex_name: str
    machine_id: str
    pq_gen: complex


@dataclass(frozen=True)
class RawMachines:
    number: list[int]
    ex_name: list[str]
    machine_id: list[str]
    pq_gen: list[complex]


class Machines:
    def __init__(self) -> None:
        self._raw_machines: RawMachines = RawMachines(
            wf.amachint(string="number")[0],
            wf.amachchar(string="exName")[0],
            wf.amachchar(string="id")[0],
            wf.amachcplx(string="pqGen")[0],
        )

    def __iter__(self) -> Iterator[Machine]:
        for machine_idx in range(len(self)):
            yield Machine(
                self._raw_machines.number[machine_idx],
                self._raw_machines.ex_name[machine_idx],
                self._raw_machines.machine_id[machine_idx],
                self._raw_machines.pq_gen[machine_idx],
            )

    def __len__(self) -> int:
        return len(self._raw_machines.number)


class TemporaryBusLoad:
    TEMP_LOAD_ID: str = "Tm"

    def __init__(self, bus: Bus) -> None:
        self._bus: Bus = bus
        self._context_manager_is_active: bool = False
        self._load_mva: complex

    def __enter__(self) -> None:
        # Create load
        wf.load_data_6(
            self._bus.number,
            self.TEMP_LOAD_ID,
            realar=[self._load_mva.real, self._load_mva.imag],
        )
        self._context_manager_is_active = True

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        # Delete load
        wf.purgload(self._bus.number, self.TEMP_LOAD_ID)
        self._context_manager_is_active = False

    def __call__(self, load_mva: complex) -> "TemporaryBusLoad":
        self._load_mva = load_mva
        return self


class TemporaryBusMachine:
    TEMP_MACHINE_ID: str = "Tm"

    def __init__(self, bus: Bus) -> None:
        self._bus: Bus = bus
        self._context_manager_is_active: bool = False
        self._gen_mva: complex

    def __enter__(self) -> None:
        # Create machine
        wf.machine_data_4(
            self._bus.number,
            self.TEMP_MACHINE_ID,
            realar=[self._gen_mva.real, self._gen_mva.imag],
        )
        self._context_manager_is_active = True

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        # Delete machine
        wf.purgmac(self._bus.number, self.TEMP_MACHINE_ID)
        self._context_manager_is_active = False

    def __call__(self, gen_mva: complex) -> "TemporaryBusMachine":
        self._gen_mva = gen_mva
        return self


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
