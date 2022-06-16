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
import dataclasses
import logging
import os
import sys
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from types import TracebackType
from typing import Final, Iterator, Optional, Union, overload

PANDAPOWER_BACKEND: bool = os.getenv("GRID_CAPACITY_PANDAPOWER_BACKEND") is not None
if sys.platform == "win32" and not PANDAPOWER_BACKEND:
    import psspy

    from pssetools import wrapped_funcs as wf
else:
    import gridcapacity.backends.pandapower as pp_backend

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Branch:
    from_number: int
    to_number: int
    branch_id: str = "1"

    def is_enabled(self) -> bool:
        """Return `True` if is enabled."""
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            status: int = wf.brnint(
                self.from_number, self.to_number, self.branch_id, "STATUS"
            )
            return status != 0
        else:
            branch_idx: int = get_pp_branch_idx(self)
            return pp_backend.net.line.in_service[branch_idx]


def get_pp_branch_idx(branch: Branch) -> int:
    """Returns index of a given branch of a PandaPower network."""
    for idx in range(len(pp_backend.net.line)):
        if (
            pp_backend.net.line.from_bus[idx] == branch.from_number
            and pp_backend.net.line.to_bus[idx] == branch.to_number
        ):
            return idx
    raise KeyError(f"{branch=} not found!")


@dataclass
class PsseBranches:
    from_number: list[int]
    to_number: list[int]
    branch_id: list[str]
    pct_rate: list[float]


class Branches(Sequence):
    def __init__(self, rate: str = "Rate1") -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._rate: str = rate
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            self._psse_branches: PsseBranches = PsseBranches(
                wf.abrnint(string="fromNumber")[0],
                wf.abrnint(string="toNumber")[0],
                wf.abrnchar(string="id")[0],
                wf.abrnreal(string=f"pct{self._rate}")[0],
            )

    @overload
    def __getitem__(self, idx: int) -> Branch:
        ...

    @overload
    def __getitem__(self, idx: slice) -> tuple[Branch, ...]:
        ...

    def __getitem__(self, idx: Union[int, slice]) -> Union[Branch, tuple[Branch, ...]]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            if isinstance(idx, int):
                return Branch(
                    self._psse_branches.from_number[idx],
                    self._psse_branches.to_number[idx],
                    self._psse_branches.branch_id[idx],
                )
            elif isinstance(idx, slice):
                return tuple(
                    Branch(*args)
                    for args in zip(
                        self._psse_branches.from_number[idx],
                        self._psse_branches.to_number[idx],
                        self._psse_branches.branch_id[idx],
                    )
                )
        else:

            def branch_from_pp(from_bus: int, to_bus: int, parallel: int) -> Branch:
                """Make a branch from PandaPower fields.

                The PandaPower `parallel` field is used in place of the PSSE branch ID field
                because PSSE uses distinct branch IDs for parallel connections only.
                """
                return Branch(
                    from_number=from_bus, to_number=to_bus, branch_id=str(parallel)
                )

            if isinstance(idx, int):
                return branch_from_pp(
                    pp_backend.net.line.from_bus[idx],
                    pp_backend.net.line.to_bus[idx],
                    pp_backend.net.line.parallel[idx],
                )
            elif isinstance(idx, slice):
                return tuple(
                    branch_from_pp(*args)
                    for args in zip(
                        pp_backend.net.line.from_bus[idx],
                        pp_backend.net.line.to_bus[idx],
                        pp_backend.net.line.parallel[idx],
                    )
                )

    def __len__(self) -> int:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return len(self._psse_branches.from_number)
        else:
            return len(pp_backend.net.line.from_bus)

    def __iter__(self) -> Iterator[Branch]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        for i in range(len(self)):
            yield self[i]
        return

    def get_overloaded_indexes(self, max_branch_loading_pct: float) -> tuple[int, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            loadings_pct = self._psse_branches.pct_rate
        else:
            loadings_pct = pp_backend.net.res_line.loading_percent
        return tuple(
            branch_idx
            for branch_idx, pct_rate in enumerate(loadings_pct)
            if pct_rate > max_branch_loading_pct
        )

    def get_loading_pct(
        self,
        selected_indexes: tuple[int, ...],
    ) -> tuple[float, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return tuple(self._psse_branches.pct_rate[idx] for idx in selected_indexes)
        else:
            return tuple(
                pp_backend.net.res_line.loading_percent[idx] for idx in selected_indexes
            )

    def log(
        self,
        level: int,
        selected_indexes: Optional[tuple[int, ...]] = None,
    ) -> None:
        if not log.isEnabledFor(level):
            return
        branch_fields: tuple[str, ...] = tuple(
            (*dataclasses.asdict(self[0]).keys(), f"pct{self._rate}")
        )
        self._log.log(level, branch_fields)
        for idx, branch in enumerate(self):
            if selected_indexes is None or idx in selected_indexes:
                if sys.platform == "win32" and not PANDAPOWER_BACKEND:
                    loading_pct = self._psse_branches.pct_rate[idx]
                else:
                    loading_pct = pp_backend.net.res_line.loading_percent[idx]
                self._log.log(
                    level,
                    tuple(
                        (
                            *dataclasses.astuple(branch),
                            loading_pct,
                        )
                    ),
                )
        self._log.log(level, branch_fields)


@contextmanager
def disable_branch(branch: Branch) -> Iterator[bool]:
    is_disabled: bool = False
    if sys.platform == "win32" and not PANDAPOWER_BACKEND:
        try:
            error_code: int = psspy.branch_chng_3(
                branch.from_number, branch.to_number, branch.branch_id, st=0
            )
            if error_code == 0:
                is_disabled = True
                yield True
            else:
                log.info(f"Failed disabling branch {branch=} {error_code=}")
                yield False
        finally:
            if is_disabled:
                wf.branch_chng_3(
                    branch.from_number, branch.to_number, branch.branch_id, st=1
                )
    else:
        branch_idx: int
        try:
            branch_idx = get_pp_branch_idx(branch)
            pp_backend.net.line.in_service[branch_idx] = False
            is_disabled = True
            yield True
        except KeyError:
            yield False
        finally:
            if is_disabled:
                pp_backend.net.line.in_service[branch_idx] = True


@dataclass(frozen=True)
class Bus:
    number: int
    ex_name: str
    type: int


@dataclass
class PsseBuses:
    number: list[int]
    ex_name: list[str]
    type: list[int]
    pu: list[float]


class Buses(Sequence):
    def __init__(self) -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            self._psse_buses: PsseBuses = PsseBuses(
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
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            if isinstance(idx, int):
                return Bus(
                    self._psse_buses.number[idx],
                    self._psse_buses.ex_name[idx],
                    self._psse_buses.type[idx],
                )
            elif isinstance(idx, slice):
                return tuple(
                    Bus(*args)
                    for args in zip(
                        self._psse_buses.number[idx],
                        self._psse_buses.ex_name[idx],
                        self._psse_buses.type[idx],
                    )
                )
        else:

            def bus_from_pp(name: int, vn_kv: float, zone: float, bus_type: str) -> Bus:
                return Bus(
                    number=name,
                    ex_name=f"{vn_kv} {zone}",
                    type=1 if bus_type == "b" else 0,
                )

            if isinstance(idx, int):
                return bus_from_pp(
                    pp_backend.net.bus.name[idx],
                    pp_backend.net.bus.vn_kv[idx],
                    pp_backend.net.bus.zone[idx],
                    pp_backend.net.bus.type[idx],
                )
            elif isinstance(idx, slice):
                return tuple(
                    bus_from_pp(*args)
                    for args in zip(
                        pp_backend.net.bus.name[idx],
                        pp_backend.net.bus.vn_kv[idx],
                        pp_backend.net.bus.zone[idx],
                        pp_backend.net.bus.type[idx],
                    )
                )

    def __len__(self) -> int:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return len(self._psse_buses.number)
        else:
            return len(pp_backend.net.bus.name)

    def __iter__(self) -> Iterator[Bus]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        for i in range(len(self)):
            yield self[i]
        return

    def get_overvoltage_indexes(self, max_bus_voltage: float) -> tuple[int, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            pu_voltages = self._psse_buses.pu
        else:
            pu_voltages = pp_backend.net.res_bus.vm_pu
        return tuple(
            bus_id
            for bus_id, pu_voltage in enumerate(pu_voltages)
            if pu_voltage > max_bus_voltage
        )

    def get_undervoltage_indexes(self, min_bus_voltage: float) -> tuple[int, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            pu_voltages = self._psse_buses.pu
        else:
            pu_voltages = pp_backend.net.res_bus.vm_pu
        return tuple(
            bus_id
            for bus_id, pu_voltage in enumerate(pu_voltages)
            if pu_voltage < min_bus_voltage
        )

    def get_voltage_pu(
        self,
        selected_indexes: tuple[int, ...],
    ) -> tuple[float, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return tuple(self._psse_buses.pu[idx] for idx in selected_indexes)
        else:
            return tuple(pp_backend.net.res_bus.vm_pu[idx] for idx in selected_indexes)

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
                pu: float
                if sys.platform == "win32" and not PANDAPOWER_BACKEND:
                    pu = self._psse_buses.pu[idx]
                else:
                    pu = pp_backend.net.res_bus.vm_pu[idx]
                self._log.log(
                    level,
                    tuple((*dataclasses.astuple(bus), pu)),
                )
        self._log.log(level, bus_fields)


# @dataclass(frozen=True)
# class Load:
#     number: int
#     ex_name: str
#     load_id: str
#     mva_act: complex
#
#
# @dataclass(frozen=True)
# class RawLoads:
#     number: list[int]
#     ex_name: list[str]
#     load_id: list[str]
#     mva_act: list[complex]
#
#
# class Loads:
#     def __init__(self) -> None:
#         self._raw_loads: RawLoads = RawLoads(
#             wf.aloadint(string="number")[0],
#             wf.aloadchar(string="exName")[0],
#             wf.aloadchar(string="id")[0],
#             wf.aloadcplx(string="mvaAct")[0],
#         )
#
#     def __iter__(self) -> Iterator[Load]:
#         for load_idx in range(len(self)):
#             yield Load(
#                 self._raw_loads.number[load_idx],
#                 self._raw_loads.ex_name[load_idx],
#                 self._raw_loads.load_id[load_idx],
#                 self._raw_loads.mva_act[load_idx],
#             )
#
#     def __len__(self) -> int:
#         return len(self._raw_loads.number)
#
#
# @dataclass(frozen=True)
# class Machine:
#     number: int
#     ex_name: str
#     machine_id: str
#     pq_gen: complex
#
#
# @dataclass(frozen=True)
# class RawMachines:
#     number: list[int]
#     ex_name: list[str]
#     machine_id: list[str]
#     pq_gen: list[complex]
#
#
# class Machines:
#     def __init__(self) -> None:
#         self._raw_machines: RawMachines = RawMachines(
#             wf.amachint(string="number")[0],
#             wf.amachchar(string="exName")[0],
#             wf.amachchar(string="id")[0],
#             wf.amachcplx(string="pqGen")[0],
#         )
#
#     def __iter__(self) -> Iterator[Machine]:
#         for machine_idx in range(len(self)):
#             yield Machine(
#                 self._raw_machines.number[machine_idx],
#                 self._raw_machines.ex_name[machine_idx],
#                 self._raw_machines.machine_id[machine_idx],
#                 self._raw_machines.pq_gen[machine_idx],
#             )
#
#     def __len__(self) -> int:
#         return len(self._raw_machines.number)
#
#
# class TemporaryBusLoad:
#     TEMP_LOAD_ID: str = "Tm"
#
#     def __init__(self, bus: Bus) -> None:
#         self._bus: Bus = bus
#         self._context_manager_is_active: bool = False
#         self._load_mva: complex
#
#     def __enter__(self) -> None:
#         # Create load
#         wf.load_data_6(
#             self._bus.number,
#             self.TEMP_LOAD_ID,
#             realar=[self._load_mva.real, self._load_mva.imag],
#         )
#         self._context_manager_is_active = True
#
#     def __exit__(
#         self,
#         exc_type: Optional[type[BaseException]],
#         exc_val: Optional[BaseException],
#         exc_tb: Optional[TracebackType],
#     ) -> None:
#         # Delete load
#         wf.purgload(self._bus.number, self.TEMP_LOAD_ID)
#         self._context_manager_is_active = False
#
#     def __call__(self, load_mva: complex) -> "TemporaryBusLoad":
#         self._load_mva = load_mva
#         return self
#
#     @property
#     def bus(self) -> Bus:
#         return self._bus
#
#     @property
#     def load_mva(self) -> complex:
#         return self._load_mva
#
#
# class TemporaryBusMachine:
#     TEMP_MACHINE_ID: str = "Tm"
#
#     def __init__(self, bus: Bus) -> None:
#         self._bus: Bus = bus
#         self._context_manager_is_active: bool = False
#         self._gen_mva: complex
#
#     def __enter__(self) -> None:
#         # Create machine
#         wf.machine_data_4(
#             self._bus.number,
#             self.TEMP_MACHINE_ID,
#             realar=[self._gen_mva.real, self._gen_mva.imag],
#         )
#         self._context_manager_is_active = True
#
#     def __exit__(
#         self,
#         exc_type: Optional[type[BaseException]],
#         exc_val: Optional[BaseException],
#         exc_tb: Optional[TracebackType],
#     ) -> None:
#         # Delete machine
#         wf.purgmac(self._bus.number, self.TEMP_MACHINE_ID)
#         self._context_manager_is_active = False
#
#     def __call__(self, gen_mva: complex) -> "TemporaryBusMachine":
#         self._gen_mva = gen_mva
#         return self
#
#     @property
#     def bus(self) -> Bus:
#         return self._bus
#
#     @property
#     def gen_mva(self) -> complex:
#         return self._gen_mva
#
#
# TemporaryBusSubsystem = Union[TemporaryBusLoad, TemporaryBusMachine]
#
#
# @dataclass(frozen=True)
# class SwingBus:
#     number: int
#     ex_name: str
#
#
# @dataclass
# class RawSwingBuses:
#     number: list[int]
#     ex_name: list[str]
#     mva: list[float]
#
#
# class SwingBuses(Sequence):
#     def __init__(self) -> None:
#         self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
#         # PSSE returns all buses, not only swing buses
#         # Filter out all buses except swing buses (`type==3`)
#         swing_bus_type: Final[int] = 3
#         self._raw_buses: RawSwingBuses = RawSwingBuses(
#             *zip(
#                 *(
#                     (number, ex_name, mva)
#                     for number, ex_name, mva, bus_type in zip(
#                         wf.agenbusint(string="number")[0],
#                         wf.agenbuschar(string="exName")[0],
#                         wf.agenbusreal(string="mva")[0],
#                         wf.agenbusint(string="type")[0],
#                     )
#                     if bus_type == swing_bus_type
#                 )
#             )
#         )
#
#     @overload
#     def __getitem__(self, idx: int) -> SwingBus:
#         ...
#
#     @overload
#     def __getitem__(self, idx: slice) -> tuple[SwingBus, ...]:
#         ...
#
#     def __getitem__(
#         self, idx: Union[int, slice]
#     ) -> Union[SwingBus, tuple[SwingBus, ...]]:
#         if isinstance(idx, int):
#             return SwingBus(
#                 self._raw_buses.number[idx],
#                 self._raw_buses.ex_name[idx],
#             )
#         elif isinstance(idx, slice):
#             return tuple(
#                 SwingBus(*args)
#                 for args in zip(
#                     self._raw_buses.number[idx],
#                     self._raw_buses.ex_name[idx],
#                 )
#             )
#
#     def __len__(self) -> int:
#         return len(self._raw_buses.number)
#
#     def get_overloaded_indexes(self, max_swing_bus_power_mva: float) -> tuple[int, ...]:
#         return tuple(
#             bus_idx
#             for bus_idx, power_mva in enumerate(self._raw_buses.mva)
#             if power_mva > max_swing_bus_power_mva
#         )
#
#     def get_power_mva(
#         self,
#         selected_indexes: tuple[int, ...],
#     ) -> tuple[float, ...]:
#         return tuple(self._raw_buses.mva[idx] for idx in selected_indexes)
#
#     def log(
#         self,
#         level: int,
#         selected_indexes: Optional[tuple[int, ...]] = None,
#     ) -> None:
#         if not log.isEnabledFor(level):
#             return
#         bus_fields: tuple[str, ...] = tuple(
#             (*dataclasses.asdict(self[0]).keys(), "mva")
#         )
#         self._log.log(level, bus_fields)
#         for idx, bus in enumerate(self):
#             if selected_indexes is None or idx in selected_indexes:
#                 self._log.log(
#                     level,
#                     tuple((*dataclasses.astuple(bus), self._raw_buses.mva[idx])),
#                 )
#         self._log.log(level, bus_fields)
#
#
# @dataclass(frozen=True)
# class Trafo:
#     from_number: int
#     to_number: int
#     trafo_id: str = "1"
#
#     def is_enabled(self) -> bool:
#         """Return `True` if is enabled"""
#         # Trafo status is available through the branches `brnint` API only.
#         # It isn't available through the trafos `xfrint` API.
#         status: int = wf.brnint(
#             self.from_number, self.to_number, self.trafo_id, "STATUS"
#         )
#         return status != 0
#
#
# @dataclass
# class RawTrafos:
#     from_number: list[int]
#     to_number: list[int]
#     trafo_id: list[str]
#     pct_rate: list[float]
#
#
# class Trafos(Sequence):
#     def __init__(self, rate: str = "Rate1") -> None:
#         self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
#         self._rate: str = rate
#         self._raw_trafos: RawTrafos = RawTrafos(
#             wf.atrnint(string="fromNumber")[0],
#             wf.atrnint(string="toNumber")[0],
#             wf.atrnchar(string="id")[0],
#             wf.atrnreal(string=f"pct{self._rate}")[0],
#         )
#
#     @overload
#     def __getitem__(self, idx: int) -> Trafo:
#         ...
#
#     @overload
#     def __getitem__(self, idx: slice) -> tuple[Trafo, ...]:
#         ...
#
#     def __getitem__(self, idx: Union[int, slice]) -> Union[Trafo, tuple[Trafo, ...]]:
#         if isinstance(idx, int):
#             return Trafo(
#                 self._raw_trafos.from_number[idx],
#                 self._raw_trafos.to_number[idx],
#                 self._raw_trafos.trafo_id[idx],
#             )
#         elif isinstance(idx, slice):
#             return tuple(
#                 Trafo(*args)
#                 for args in zip(
#                     self._raw_trafos.from_number[idx],
#                     self._raw_trafos.to_number[idx],
#                     self._raw_trafos.trafo_id[idx],
#                 )
#             )
#
#     def __len__(self) -> int:
#         return len(self._raw_trafos.from_number)
#
#     def get_overloaded_indexes(self, max_trafo_loading_pct: float) -> tuple[int, ...]:
#         return tuple(
#             trafo_idx
#             for trafo_idx, pct_rate in enumerate(self._raw_trafos.pct_rate)
#             if pct_rate > max_trafo_loading_pct
#         )
#
#     def get_loading_pct(
#         self,
#         selected_indexes: tuple[int, ...],
#     ) -> tuple[float, ...]:
#         return tuple(self._raw_trafos.pct_rate[idx] for idx in selected_indexes)
#
#     def log(
#         self,
#         level: int,
#         selected_indexes: Optional[tuple[int, ...]] = None,
#     ) -> None:
#         if not log.isEnabledFor(level):
#             return
#         trafo_fields: tuple[str, ...] = tuple(
#             (*dataclasses.asdict(self[0]).keys(), f"pct{self._rate}")
#         )
#         self._log.log(level, trafo_fields)
#         for idx, trafo in enumerate(self):
#             if selected_indexes is None or idx in selected_indexes:
#                 self._log.log(
#                     level,
#                     tuple(
#                         (
#                             *dataclasses.astuple(trafo),
#                             self._raw_trafos.pct_rate[idx],
#                         )
#                     ),
#                 )
#         self._log.log(level, trafo_fields)
#
#
# @contextmanager
# def disable_trafo(trafo: Trafo) -> Iterator[bool]:
#     is_disabled: bool = False
#     try:
#         error_code, _ = psspy.two_winding_chng_6(
#             trafo.from_number, trafo.to_number, trafo.trafo_id, intgar1=0
#         )
#         if error_code == 0:
#             is_disabled = True
#             yield is_disabled
#         else:
#             log.info(f"Failed disabling trafo {trafo=} {error_code=}")
#             yield is_disabled
#     finally:
#         if is_disabled:
#             wf.two_winding_chng_6(
#                 trafo.from_number, trafo.to_number, trafo.trafo_id, intgar1=1
#             )
#
#
# @dataclass(frozen=True)
# class Trafo3w:
#     wind1_number: int
#     wind2_number: int
#     wind3_number: int
#     trafo_id: str
#
#     def is_enabled(self) -> bool:
#         """Return `True` if is enabled"""
#         # Trafo status is available through the branches `brnint` API only.
#         status: int = wf.brnint(
#             self.wind1_number, self.wind2_number, self.trafo_id, "STATUS"
#         )
#         return status != 0
#
#
# @dataclass
# class RawTrafos3w:
#     wind1_number: list[int]
#     wind2_number: list[int]
#     wind3_number: list[int]
#     trafo_id: list[str]
#     pct_rate: list[float]
#
#
# class Trafos3w(Sequence):
#     def __init__(self, rate: str = "Rate1") -> None:
#         self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
#         self._rate: str = rate
#         self._raw_trafos: RawTrafos3w = RawTrafos3w(
#             wf.awndint(string="wind1Number")[0],
#             wf.awndint(string="wind2Number")[0],
#             wf.awndint(string="wind3Number")[0],
#             wf.awndchar(string="id")[0],
#             wf.awndreal(string=f"pct{self._rate}")[0],
#         )
#
#     @overload
#     def __getitem__(self, idx: int) -> Trafo3w:
#         ...
#
#     @overload
#     def __getitem__(self, idx: slice) -> tuple[Trafo3w, ...]:
#         ...
#
#     def __getitem__(
#         self, idx: Union[int, slice]
#     ) -> Union[Trafo3w, tuple[Trafo3w, ...]]:
#         if isinstance(idx, int):
#             return Trafo3w(
#                 self._raw_trafos.wind1_number[idx],
#                 self._raw_trafos.wind2_number[idx],
#                 self._raw_trafos.wind3_number[idx],
#                 self._raw_trafos.trafo_id[idx],
#             )
#         elif isinstance(idx, slice):
#             return tuple(
#                 Trafo3w(*args)
#                 for args in zip(
#                     self._raw_trafos.wind1_number[idx],
#                     self._raw_trafos.wind2_number[idx],
#                     self._raw_trafos.wind3_number[idx],
#                     self._raw_trafos.trafo_id[idx],
#                 )
#             )
#
#     def __len__(self) -> int:
#         return len(self._raw_trafos.wind1_number)
#
#     def get_overloaded_indexes(self, max_trafo_loading_pct: float) -> tuple[int, ...]:
#         return tuple(
#             trafo_idx
#             for trafo_idx, pct_rate in enumerate(self._raw_trafos.pct_rate)
#             if pct_rate > max_trafo_loading_pct
#         )
#
#     def get_loading_pct(
#         self,
#         selected_indexes: tuple[int, ...],
#     ) -> tuple[float, ...]:
#         return tuple(self._raw_trafos.pct_rate[idx] for idx in selected_indexes)
#
#     def log(
#         self,
#         level: int,
#         selected_indexes: Optional[tuple[int, ...]] = None,
#     ) -> None:
#         if not log.isEnabledFor(level):
#             return
#         trafo_fields: tuple[str, ...] = tuple(
#             (*dataclasses.asdict(self[0]).keys(), f"pct{self._rate}")
#         )
#         self._log.log(level, trafo_fields)
#         for idx, trafo in enumerate(self):
#             if selected_indexes is None or idx in selected_indexes:
#                 self._log.log(
#                     level,
#                     tuple(
#                         (
#                             *dataclasses.astuple(trafo),
#                             self._raw_trafos.pct_rate[idx],
#                         )
#                     ),
#                 )
#         self._log.log(level, trafo_fields)
#
#
# Subsystems = Union[Buses, Branches, SwingBuses, Trafos, Trafos3w]
Subsystems = Union[Buses, Branches]
