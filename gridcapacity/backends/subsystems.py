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
from pprint import pformat
from types import TracebackType
from typing import Final, Iterable, Iterator, Optional, Union, overload

PANDAPOWER_BACKEND: bool = os.getenv("GRID_CAPACITY_PANDAPOWER_BACKEND") is not None
if sys.platform == "win32" and not PANDAPOWER_BACKEND:
    import psspy

    from .psse import wrapped_funcs as wf
else:
    import pandapower as pp

    from . import pandapower as pp_backend

log = logging.getLogger(__name__)


class Printable:
    def __str__(self: Iterable) -> str:
        return pformat(tuple(f"{idx}: {instance}" for idx, instance in enumerate(self)))


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
        branch_idx: int = self.pp_idx
        return pp_backend.net.line.in_service[branch_idx]

    if sys.platform != "win32" or PANDAPOWER_BACKEND:

        @property
        def pp_idx(self) -> int:
            """Returns index in a PandaPower network."""
            for idx, line in pp_backend.net.line.iterrows():
                if (
                    line["from_bus"] == self.from_number
                    and line["to_bus"] == self.to_number
                ):
                    return idx
            raise KeyError(f"{self} not found!")


@dataclass
class PsseBranches:
    from_number: list[int]
    to_number: list[int]
    branch_id: list[str]
    pct_rate: list[float]


class Branches(Sequence, Printable):
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
            if isinstance(idx, slice):
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
            if isinstance(idx, slice):
                return tuple(
                    branch_from_pp(*args)
                    for args in zip(
                        pp_backend.net.line.from_bus[idx],
                        pp_backend.net.line.to_bus[idx],
                        pp_backend.net.line.parallel[idx],
                    )
                )
        raise RuntimeError(f"Wrong index {idx}")

    def __len__(self) -> int:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return len(self._psse_branches.from_number)
        return len(pp_backend.net.line)

    def __iter__(self) -> Iterator[Branch]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        for i in range(len(self)):
            yield self[i]

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
                log.info(
                    "Failed disabling branch %s, error_code=%s", branch, error_code
                )
                yield False
        finally:
            if is_disabled:
                wf.branch_chng_3(
                    branch.from_number, branch.to_number, branch.branch_id, st=1
                )
    else:
        branch_idx: int
        try:
            branch_idx = branch.pp_idx
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
    if sys.platform != "win32" or PANDAPOWER_BACKEND:

        @property
        def pp_idx(self) -> int:
            """Returns index in a PandaPower network."""
            for idx, bus in pp_backend.net.bus.iterrows():
                if bus["name"] == self.number:
                    return idx
            raise KeyError(f"{self} not found!")


@dataclass
class PsseBuses:
    number: list[int]
    ex_name: list[str]
    type: list[int]
    pu: list[float]


class Buses(Sequence, Printable):
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
            if isinstance(idx, slice):
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
            if isinstance(idx, slice):
                return tuple(
                    bus_from_pp(*args)
                    for args in zip(
                        pp_backend.net.bus.name[idx],
                        pp_backend.net.bus.vn_kv[idx],
                        pp_backend.net.bus.zone[idx],
                        pp_backend.net.bus.type[idx],
                    )
                )
        raise RuntimeError(f"Wrong index {idx}")

    def __len__(self) -> int:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return len(self._psse_buses.number)
        return len(pp_backend.net.bus)

    def __iter__(self) -> Iterator[Bus]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        for i in range(len(self)):
            yield self[i]

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


@dataclass(frozen=True)
class Load:
    number: int
    ex_name: str
    load_id: str
    mva_act: complex


@dataclass(frozen=True)
class PsseLoads:
    number: list[int]
    ex_name: list[str]
    load_id: list[str]
    mva_act: list[complex]


class Loads(Printable):
    def __init__(self) -> None:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            self._raw_loads: PsseLoads = PsseLoads(
                wf.aloadint(string="number")[0],
                wf.aloadchar(string="exName")[0],
                wf.aloadchar(string="id")[0],
                wf.aloadcplx(string="mvaAct")[0],
            )

    def __iter__(self) -> Iterator[Load]:
        for load_idx in range(len(self)):
            if sys.platform == "win32" and not PANDAPOWER_BACKEND:
                yield Load(
                    self._raw_loads.number[load_idx],
                    self._raw_loads.ex_name[load_idx],
                    self._raw_loads.load_id[load_idx],
                    self._raw_loads.mva_act[load_idx],
                )
            else:
                yield Load(
                    pp_backend.net.bus.name[pp_backend.net.load.bus[load_idx]],
                    "",
                    pp_backend.net.load.name[load_idx],
                    pp_backend.net.load.p_mw[load_idx]
                    + 1j * pp_backend.net.load.q_mvar[load_idx],
                )

    def __len__(self) -> int:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return len(self._raw_loads.number)
        return len(pp_backend.net.load)


@dataclass(frozen=True)
class Machine:
    number: int
    ex_name: str
    machine_id: str
    pq_gen: complex


@dataclass(frozen=True)
class PsseMachines:
    number: list[int]
    ex_name: list[str]
    machine_id: list[str]
    pq_gen: list[complex]


class Machines(Printable):
    def __init__(self) -> None:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            self._raw_machines: PsseMachines = PsseMachines(
                wf.amachint(string="number")[0],
                wf.amachchar(string="exName")[0],
                wf.amachchar(string="id")[0],
                wf.amachcplx(string="pqGen")[0],
            )

    def __iter__(self) -> Iterator[Machine]:
        for machine_idx in range(len(self)):
            if sys.platform == "win32" and not PANDAPOWER_BACKEND:
                yield Machine(
                    self._raw_machines.number[machine_idx],
                    self._raw_machines.ex_name[machine_idx],
                    self._raw_machines.machine_id[machine_idx],
                    self._raw_machines.pq_gen[machine_idx],
                )
            else:
                yield Machine(
                    pp_backend.net.bus.name[pp_backend.net.sgen.bus[machine_idx]],
                    "",
                    pp_backend.net.sgen.name[machine_idx],
                    pp_backend.net.sgen.p_mw[machine_idx]
                    + 1j * pp_backend.net.sgen.q_mvar[machine_idx],
                )

    def __len__(self) -> int:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return len(self._raw_machines.number)
        return len(pp_backend.net.sgen)


class TemporaryBusLoad:
    TEMP_LOAD_ID: str = "Tm"

    def __init__(self, bus: Bus) -> None:
        self._bus: Bus = bus
        self._load_mva: complex

    def __enter__(self) -> None:
        # Create load
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            wf.load_data_6(
                self._bus.number,
                self.TEMP_LOAD_ID,
                realar=[self._load_mva.real, self._load_mva.imag],
            )
        else:
            pp.create_load(
                pp_backend.net,
                self._bus.pp_idx,
                self._load_mva.real,
                self._load_mva.imag,
                name=self.TEMP_LOAD_ID,
            )

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        # Delete load
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            wf.purgload(self._bus.number, self.TEMP_LOAD_ID)
        else:
            pp_backend.net.load = pp_backend.net.load.drop(
                pp_backend.net.load[pp_backend.net.load.name == self.TEMP_LOAD_ID].index
            )

    def __call__(self, load_mva: complex) -> "TemporaryBusLoad":
        self._load_mva = load_mva
        return self

    @property
    def bus(self) -> Bus:
        return self._bus

    @property
    def load_mva(self) -> complex:
        return self._load_mva


class TemporaryBusMachine:
    TEMP_MACHINE_ID: str = "Tm"

    def __init__(self, bus: Bus) -> None:
        self._bus: Bus = bus
        self._gen_mva: complex

    def __enter__(self) -> None:
        # Create machine
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            wf.machine_data_4(
                self._bus.number,
                self.TEMP_MACHINE_ID,
                realar=[self._gen_mva.real, self._gen_mva.imag],
            )
        else:
            pp.create_sgen(
                pp_backend.net,
                self._bus.pp_idx,
                self._gen_mva.real,
                self._gen_mva.imag,
                name=self.TEMP_MACHINE_ID,
            )

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        # Delete machine
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            wf.purgmac(self._bus.number, self.TEMP_MACHINE_ID)
        else:
            pp_backend.net.sgen = pp_backend.net.sgen.drop(
                pp_backend.net.sgen[
                    pp_backend.net.sgen.name == self.TEMP_MACHINE_ID
                ].index
            )

    def __call__(self, gen_mva: complex) -> "TemporaryBusMachine":
        self._gen_mva = gen_mva
        return self

    @property
    def bus(self) -> Bus:
        return self._bus

    @property
    def gen_mva(self) -> complex:
        return self._gen_mva


TemporaryBusSubsystem = Union[TemporaryBusLoad, TemporaryBusMachine]


@dataclass(frozen=True)
class SwingBus:
    number: int
    ex_name: str


@dataclass
class PsseSwingBuses:
    number: list[int]
    ex_name: list[str]
    pgen: list[float]


class SwingBuses(Sequence, Printable):
    def __init__(self) -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            # PSSE returns all buses, not only swing buses
            # Filter out all buses except swing buses (`type==3`)
            swing_bus_type: Final[int] = 3
            self._raw_buses: PsseSwingBuses = PsseSwingBuses(
                *zip(
                    *(
                        (number, ex_name, pgen)
                        for number, ex_name, pgen, bus_type in zip(
                            wf.agenbusint(string="number")[0],
                            wf.agenbuschar(string="exName")[0],
                            wf.agenbusreal(string="pgen")[0],
                            wf.agenbusint(string="type")[0],
                        )
                        if bus_type == swing_bus_type
                    )
                )
            )

    @overload
    def __getitem__(self, idx: int) -> SwingBus:
        ...

    @overload
    def __getitem__(self, idx: slice) -> tuple[SwingBus, ...]:
        ...

    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[SwingBus, tuple[SwingBus, ...]]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            if isinstance(idx, int):
                return SwingBus(
                    self._raw_buses.number[idx],
                    self._raw_buses.ex_name[idx],
                )
            if isinstance(idx, slice):
                return tuple(
                    SwingBus(*args)
                    for args in zip(
                        self._raw_buses.number[idx],
                        self._raw_buses.ex_name[idx],
                    )
                )
        else:

            def swing_bus_from_pp(bus: int, vm_pu: float, max_p_mw: float) -> SwingBus:
                return SwingBus(
                    number=bus,
                    ex_name=f"{vm_pu} {max_p_mw}",
                )

            if isinstance(idx, int):
                return swing_bus_from_pp(
                    pp_backend.net.ext_grid.bus[idx],
                    pp_backend.net.ext_grid.vm_pu[idx],
                    pp_backend.net.ext_grid.max_p_mw[idx],
                )
            if isinstance(idx, slice):
                return tuple(
                    swing_bus_from_pp(*args)
                    for args in zip(
                        pp_backend.net.ext_grid.bus[idx],
                        pp_backend.net.ext_grid.vm_pu[idx],
                        pp_backend.net.ext_grid.max_p_mw[idx],
                    )
                )
        raise RuntimeError(f"Wrong index {idx}")

    def __len__(self) -> int:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return len(self._raw_buses.number)
        return len(pp_backend.net.ext_grid)

    def __iter__(self) -> Iterator[SwingBus]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        for i in range(len(self)):
            yield self[i]

    def get_overloaded_indexes(
        self, max_swing_bus_power_p_mw: float
    ) -> tuple[int, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            powers_p_mw = self._raw_buses.pgen
        else:
            powers_p_mw = pp_backend.net.res_ext_grid.p_mw
        return tuple(
            bus_idx
            for bus_idx, power_p_mw in enumerate(powers_p_mw)
            if power_p_mw > max_swing_bus_power_p_mw
        )

    def get_power_p_mw(
        self,
        selected_indexes: tuple[int, ...],
    ) -> tuple[float, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return tuple(self._raw_buses.pgen[idx] for idx in selected_indexes)
        return tuple(pp_backend.net.res_ext_grid.p_mw[idx] for idx in selected_indexes)

    def log(
        self,
        level: int,
        selected_indexes: Optional[tuple[int, ...]] = None,
    ) -> None:
        if not log.isEnabledFor(level):
            return
        bus_fields: tuple[str, ...] = tuple(
            (*dataclasses.asdict(self[0]).keys(), "pgen")
        )
        self._log.log(level, bus_fields)
        for idx, bus in enumerate(self):
            if selected_indexes is None or idx in selected_indexes:
                p_mw: float
                if sys.platform == "win32" and not PANDAPOWER_BACKEND:
                    p_mw = self._raw_buses.pgen[idx]
                else:
                    p_mw = pp_backend.net.res_ext_grid.p_mw[idx]
                self._log.log(
                    level,
                    tuple((*dataclasses.astuple(bus), p_mw)),
                )
        self._log.log(level, bus_fields)


@dataclass(frozen=True)
class Trafo:
    from_number: int
    to_number: int
    trafo_id: str = "1"

    def is_enabled(self) -> bool:
        """Return `True` if is enabled"""
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            # Trafo status is available through the branches `brnint` API only.
            # It isn't available through the trafos `xfrint` API.
            status: int = wf.brnint(
                self.from_number, self.to_number, self.trafo_id, "STATUS"
            )
            return status != 0
        trafo_idx: int = self.pp_idx
        return pp_backend.net.trafo.in_service[trafo_idx]

    if sys.platform != "win32" or PANDAPOWER_BACKEND:

        @property
        def pp_idx(self) -> int:
            """Returns index in a PandaPower network."""
            for idx, trafo in pp_backend.net.trafo.iterrows():
                if (
                    trafo["hv_bus"] == self.from_number
                    and trafo["lv_bus"] == self.to_number
                ):
                    return idx
            raise KeyError(f"{self} not found!")


@dataclass
class PsseTrafos:
    from_number: list[int]
    to_number: list[int]
    trafo_id: list[str]
    pct_rate: list[float]


class Trafos(Sequence, Printable):
    def __init__(self, rate: str = "Rate1") -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._rate: str = rate
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            self._raw_trafos: PsseTrafos = PsseTrafos(
                wf.atrnint(string="fromNumber")[0],
                wf.atrnint(string="toNumber")[0],
                wf.atrnchar(string="id")[0],
                wf.atrnreal(string=f"pct{self._rate}")[0],
            )

    @overload
    def __getitem__(self, idx: int) -> Trafo:
        ...

    @overload
    def __getitem__(self, idx: slice) -> tuple[Trafo, ...]:
        ...

    def __getitem__(self, idx: Union[int, slice]) -> Union[Trafo, tuple[Trafo, ...]]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            if isinstance(idx, int):
                return Trafo(
                    self._raw_trafos.from_number[idx],
                    self._raw_trafos.to_number[idx],
                    self._raw_trafos.trafo_id[idx],
                )
            if isinstance(idx, slice):
                return tuple(
                    Trafo(*args)
                    for args in zip(
                        self._raw_trafos.from_number[idx],
                        self._raw_trafos.to_number[idx],
                        self._raw_trafos.trafo_id[idx],
                    )
                )
        else:

            def trafo_from_pp(hv_bus: int, lv_bus: int, parallel: int) -> Trafo:
                """Make a transformer from PandaPower fields.

                The PandaPower `parallel` field is used in place of the PSSE transformer ID field
                because PSSE uses distinct transformer IDs for parallel connections only.
                """
                return Trafo(
                    from_number=hv_bus, to_number=lv_bus, trafo_id=str(parallel)
                )

            if isinstance(idx, int):
                return trafo_from_pp(
                    pp_backend.net.trafo.hv_bus[idx],
                    pp_backend.net.trafo.lv_bus[idx],
                    pp_backend.net.trafo.parallel[idx],
                )
            if isinstance(idx, slice):
                return tuple(
                    trafo_from_pp(*args)
                    for args in zip(
                        pp_backend.net.trafo.hv_bus[idx],
                        pp_backend.net.trafo.lv_bus[idx],
                        pp_backend.net.trafo.parallel[idx],
                    )
                )
        raise RuntimeError(f"Wrong index {idx}")

    def __len__(self) -> int:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return len(self._raw_trafos.from_number)
        return len(pp_backend.net.trafo)

    def __iter__(self) -> Iterator[Trafo]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        for i in range(len(self)):
            yield self[i]

    def get_overloaded_indexes(self, max_trafo_loading_pct: float) -> tuple[int, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            loadings_pct = self._raw_trafos.pct_rate
        else:
            loadings_pct = pp_backend.net.res_trafo.loading_percent
        return tuple(
            trafo_idx
            for trafo_idx, pct_rate in enumerate(loadings_pct)
            if pct_rate > max_trafo_loading_pct
        )

    def get_loading_pct(
        self,
        selected_indexes: tuple[int, ...],
    ) -> tuple[float, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return tuple(self._raw_trafos.pct_rate[idx] for idx in selected_indexes)
        return tuple(
            pp_backend.net.res_trafo.loading_percent[idx] for idx in selected_indexes
        )

    def log(
        self,
        level: int,
        selected_indexes: Optional[tuple[int, ...]] = None,
    ) -> None:
        if not log.isEnabledFor(level):
            return
        trafo_fields: tuple[str, ...] = tuple(
            (*dataclasses.asdict(self[0]).keys(), f"pct{self._rate}")
        )
        self._log.log(level, trafo_fields)
        for idx, trafo in enumerate(self):
            if selected_indexes is None or idx in selected_indexes:
                if sys.platform == "win32" and not PANDAPOWER_BACKEND:
                    loading_pct = self._raw_trafos.pct_rate[idx]
                else:
                    loading_pct = pp_backend.net.res_trafo.loading_percent[idx]
                self._log.log(
                    level,
                    tuple(
                        (
                            *dataclasses.astuple(trafo),
                            loading_pct,
                        )
                    ),
                )
        self._log.log(level, trafo_fields)


@contextmanager
def disable_trafo(trafo: Trafo) -> Iterator[bool]:
    is_disabled: bool = False
    if sys.platform == "win32" and not PANDAPOWER_BACKEND:
        try:
            error_code, _ = psspy.two_winding_chng_6(
                trafo.from_number, trafo.to_number, trafo.trafo_id, intgar1=0
            )
            if error_code == 0:
                is_disabled = True
                yield is_disabled
            else:
                log.info("Failed disabling trafo %s, error_code=%s", trafo, error_code)
                yield is_disabled
        finally:
            if is_disabled:
                wf.two_winding_chng_6(
                    trafo.from_number, trafo.to_number, trafo.trafo_id, intgar1=1
                )
    else:
        trafo_idx: int
        try:
            trafo_idx = trafo.pp_idx
            pp_backend.net.trafo.in_service[trafo_idx] = False
            is_disabled = True
            yield True
        except KeyError:
            yield False
        finally:
            if is_disabled:
                pp_backend.net.trafo.in_service[trafo_idx] = True


@dataclass(frozen=True)
class Trafo3w:
    wind1_number: int
    wind2_number: int
    wind3_number: int
    trafo_id: str

    def is_enabled(self) -> bool:
        """Return `True` if is enabled"""
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            # Trafo status is available through the branches `brnint` API only.
            status: int = wf.brnint(
                self.wind1_number, self.wind2_number, self.trafo_id, "STATUS"
            )
            return status != 0
        trafo3w_idx: int = get_pp_trafo3w_idx(self)
        return pp_backend.net.trafo3w.in_service[trafo3w_idx]


def get_pp_trafo3w_idx(trafo3w: Trafo3w) -> int:
    """Returns index of a given 3-winding transformer of a PandaPower network."""
    for idx in range(len(pp_backend.net.trafo3w)):
        if (
            pp_backend.net.trafo3w.hv_bus[idx] == trafo3w.wind1_number
            and pp_backend.net.trafo3w.mv_bus[idx] == trafo3w.wind2_number
            and pp_backend.net.trafo3w.lv_bus[idx] == trafo3w.wind3_number
        ):
            return idx
    raise KeyError(f"{trafo3w=} not found!")


@dataclass
class PsseTrafos3w:
    wind1_number: list[int]
    wind2_number: list[int]
    wind3_number: list[int]
    trafo_id: list[str]
    pct_rate: list[float]


class Trafos3w(Sequence, Printable):
    def __init__(self, rate: str = "Rate1") -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._rate: str = rate
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            self._raw_trafos: PsseTrafos3w = PsseTrafos3w(
                wf.awndint(string="wind1Number")[0],
                wf.awndint(string="wind2Number")[0],
                wf.awndint(string="wind3Number")[0],
                wf.awndchar(string="id")[0],
                wf.awndreal(string=f"pct{self._rate}")[0],
            )

    @overload
    def __getitem__(self, idx: int) -> Trafo3w:
        ...

    @overload
    def __getitem__(self, idx: slice) -> tuple[Trafo3w, ...]:
        ...

    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[Trafo3w, tuple[Trafo3w, ...]]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            if isinstance(idx, int):
                return Trafo3w(
                    self._raw_trafos.wind1_number[idx],
                    self._raw_trafos.wind2_number[idx],
                    self._raw_trafos.wind3_number[idx],
                    self._raw_trafos.trafo_id[idx],
                )
            if isinstance(idx, slice):
                return tuple(
                    Trafo3w(*args)
                    for args in zip(
                        self._raw_trafos.wind1_number[idx],
                        self._raw_trafos.wind2_number[idx],
                        self._raw_trafos.wind3_number[idx],
                        self._raw_trafos.trafo_id[idx],
                    )
                )
        else:

            def trafo3w_from_pp(
                hv_bus: int, mv_bus: int, lv_bus: int, parallel: int
            ) -> Trafo3w:
                """Make a transformer from PandaPower fields.

                The PandaPower `parallel` field is used in place of the PSSE transformer ID field
                because PSSE uses distinct transformer IDs for parallel connections only.
                """
                return Trafo3w(
                    wind1_number=hv_bus,
                    wind2_number=mv_bus,
                    wind3_number=lv_bus,
                    trafo_id=str(parallel),
                )

            if isinstance(idx, int):
                return trafo3w_from_pp(
                    pp_backend.net.trafo3w.hv_bus[idx],
                    pp_backend.net.trafo3w.mv_bus[idx],
                    pp_backend.net.trafo3w.lv_bus[idx],
                    pp_backend.net.trafo3w.parallel[idx],
                )
            if isinstance(idx, slice):
                return tuple(
                    trafo3w_from_pp(*args)
                    for args in zip(
                        pp_backend.net.trafo3w.hv_bus[idx],
                        pp_backend.net.trafo3w.mv_bus[idx],
                        pp_backend.net.trafo3w.lv_bus[idx],
                        pp_backend.net.trafo3w.parallel[idx],
                    )
                )
        raise RuntimeError(f"Wrong index {idx}")

    def __len__(self) -> int:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return len(self._raw_trafos.wind1_number)
        return len(pp_backend.net.trafo3w)

    def __iter__(self) -> Iterator[Trafo3w]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        for i in range(len(self)):
            yield self[i]

    def get_overloaded_indexes(self, max_trafo_loading_pct: float) -> tuple[int, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            loadings_pct = self._raw_trafos.pct_rate
        else:
            loadings_pct = pp_backend.net.res_trafo3w.loading_percent
        return tuple(
            trafo_idx
            for trafo_idx, pct_rate in enumerate(loadings_pct)
            if pct_rate > max_trafo_loading_pct
        )

    def get_loading_pct(
        self,
        selected_indexes: tuple[int, ...],
    ) -> tuple[float, ...]:
        if sys.platform == "win32" and not PANDAPOWER_BACKEND:
            return tuple(self._raw_trafos.pct_rate[idx] for idx in selected_indexes)
        return tuple(
            pp_backend.net.res_trafo3w.loading_percent[idx] for idx in selected_indexes
        )

    def log(
        self,
        level: int,
        selected_indexes: Optional[tuple[int, ...]] = None,
    ) -> None:
        if not log.isEnabledFor(level):
            return
        trafo_fields: tuple[str, ...] = tuple(
            (*dataclasses.asdict(self[0]).keys(), f"pct{self._rate}")
        )
        self._log.log(level, trafo_fields)
        for idx, trafo in enumerate(self):
            if selected_indexes is None or idx in selected_indexes:
                if sys.platform == "win32" and not PANDAPOWER_BACKEND:
                    loadings_pct = self._raw_trafos.pct_rate[idx]
                else:
                    loadings_pct = pp_backend.net.res_trafo3w.loading_percent[idx]
                self._log.log(
                    level,
                    tuple(
                        (
                            *dataclasses.astuple(trafo),
                            loadings_pct,
                        )
                    ),
                )
        self._log.log(level, trafo_fields)


Subsystems = Union[Buses, Branches, SwingBuses, Trafos, Trafos3w]
