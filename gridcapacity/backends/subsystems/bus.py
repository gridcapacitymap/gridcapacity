"""
Copyright 2023 Vattenfall AB

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
import sys
from abc import abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from types import TracebackType
from typing import Generic, Optional, TypeVar, Union, overload

from ...envs import envs
from .area import AreaByNumber
from .gen import Machine, Machines
from .load import Load, Loads
from .utils import Printable
from .zone import ZoneByNumber

if sys.platform == "win32" and not envs.pandapower_backend:
    import psspy

    from ..psse import wrapped_funcs as wf
else:
    import pandapower as pp

    from .. import pandapower as pp_backend

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BusBase:
    number: int

    def load_mva(self) -> complex:
        """Return sum of all bus loads."""
        actual_load_mva: complex = 0j
        loads_iterator: Iterator = iter(Loads())
        loads_available: bool = True
        try:
            load: Load = next(loads_iterator)
        except (StopIteration, KeyError):
            loads_available = False
        while loads_available:
            # Buses and loads are sorted by bus number [PSSE API.pdf].
            # So PSSE loads are iterated until load bus number is lower or equal
            # to the bus number.
            if (
                sys.platform == "win32"
                and not envs.pandapower_backend
                and load.number <= self.number
            ):
                break
            if load.number == self.number:
                actual_load_mva += load.mva_act
            try:
                load = next(loads_iterator)
            except (StopIteration, KeyError):
                loads_available = False
        return actual_load_mva

    def gen_mva(self) -> complex:
        """Return sum of all bus generators."""
        actual_gen_mva: complex = 0j
        machines_iterator: Iterator = iter(Machines())
        machines_available: bool = True
        try:
            machine: Machine = next(machines_iterator)
        except (StopIteration, KeyError):
            machines_available = False
        while machines_available:
            # Buses and machines are sorted by bus number [PSSE API.pdf].
            # So PSSE machines are iterated until machine bus number is lower or equal
            # to the bus number.
            if (
                sys.platform == "win32"
                and not envs.pandapower_backend
                and machine.number <= self.number
            ):
                break
            if machine.number == self.number:
                actual_gen_mva += machine.pq_gen
            try:
                machine = next(machines_iterator)
            except (StopIteration, KeyError):
                machines_available = False
        return actual_gen_mva


@dataclass(frozen=True)
class Bus(BusBase):
    ex_name: str
    type: int

    def add_load(self, load_mva: complex, load_id: str = "Tm") -> None:
        if sys.platform == "win32" and not envs.pandapower_backend:
            wf.load_data_6(
                self.number,
                load_id,
                realar=[load_mva.real, load_mva.imag],
            )
        else:
            pp.create_load(
                pp_backend.net,
                self.pp_idx,
                load_mva.real,
                load_mva.imag,
                name=load_id,
            )

    def add_gen(self, gen_mva: complex, gen_id: str = "Tm") -> None:
        if sys.platform == "win32" and not envs.pandapower_backend:
            wf.machine_data_4(
                self.number,
                gen_id,
                realar=[gen_mva.real, gen_mva.imag],
            )
        else:
            pp.create_sgen(
                pp_backend.net,
                self.pp_idx,
                gen_mva.real,
                gen_mva.imag,
                name=gen_id,
            )

    if sys.platform != "win32" or envs.pandapower_backend:

        @property
        def pp_idx(self) -> int:
            """Returns index in a PandaPower network."""
            for idx, bus in pp_backend.net.bus.iterrows():
                if bus["name"] == self.number:
                    return idx
            raise KeyError(f"{self} not found!")


@dataclass(frozen=True)
class DataExportBus(BusBase):
    name: str
    bus_type: int
    base_kv: float
    voltage_pu: float
    area_name: str
    area_number: int
    zone_name: str
    zone_number: int
    actual_load_mva: complex = dataclasses.field(init=False)
    actual_gen_mva: complex = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "actual_load_mva", self.load_mva())
        object.__setattr__(self, "actual_gen_mva", self.gen_mva())


GenericBus = TypeVar("GenericBus", Bus, DataExportBus)


class GenericBuses(Sequence, Printable, Generic[GenericBus]):
    def __init__(self) -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @overload
    def __getitem__(self, idx: int) -> GenericBus:
        ...

    @overload
    def __getitem__(self, idx: slice) -> tuple[GenericBus, ...]:
        ...

    @abstractmethod
    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[GenericBus, tuple[GenericBus, ...]]:
        raise NotImplementedError()

    def __len__(self) -> int:
        if sys.platform == "win32" and not envs.pandapower_backend:
            return len(self._psse_buses.number)
        return len(pp_backend.net.bus)

    def __iter__(self) -> Iterator[GenericBus]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        yield from (self[i] for i in range(len(self)))

    def get_overvoltage_indexes(self, max_bus_voltage: float) -> tuple[int, ...]:
        if sys.platform == "win32" and not envs.pandapower_backend:
            pu_voltages = self._psse_buses.pu
        else:
            pu_voltages = pp_backend.net.res_bus.vm_pu
        return tuple(
            bus_id
            for bus_id, pu_voltage in enumerate(pu_voltages)
            if pu_voltage > max_bus_voltage
        )

    def get_undervoltage_indexes(self, min_bus_voltage: float) -> tuple[int, ...]:
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        if sys.platform == "win32" and not envs.pandapower_backend:
            return tuple(self._psse_buses.pu[idx] for idx in selected_indexes)
        return tuple(pp_backend.net.res_bus.vm_pu.iat[idx] for idx in selected_indexes)

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
                if sys.platform == "win32" and not envs.pandapower_backend:
                    pu = self._psse_buses.pu[idx]
                else:
                    pu = pp_backend.net.res_bus.vm_pu.iat[idx]
                self._log.log(
                    level,
                    tuple((*dataclasses.astuple(bus), pu)),
                )
        self._log.log(level, bus_fields)


@dataclass(frozen=True)
class PsseBuses:
    number: list[int]
    ex_name: list[str]
    bus_type: list[int]
    pu: list[float]


class Buses(GenericBuses[Bus]):
    def __init__(self) -> None:
        super().__init__()
        if sys.platform == "win32" and not envs.pandapower_backend:
            self._psse_buses = PsseBuses(
                wf.abusint(string="number")[0],
                wf.abuschar(string="exName")[0],
                wf.abusint(string="type")[0],
                wf.abusreal(string="pu")[0],
            )

    def __getitem__(self, idx: Union[int, slice]) -> Union[Bus, tuple[Bus, ...]]:
        if sys.platform == "win32" and not envs.pandapower_backend:
            if isinstance(idx, int):
                return Bus(
                    self._psse_buses.number[idx],
                    self._psse_buses.ex_name[idx],
                    self._psse_buses.bus_type[idx],
                )
            if isinstance(idx, slice):
                return tuple(
                    Bus(*args)
                    for args in zip(
                        self._psse_buses.number[idx],
                        self._psse_buses.ex_name[idx],
                        self._psse_buses.bus_type[idx],
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
                    pp_backend.net.bus.name.iat[idx],
                    pp_backend.net.bus.vn_kv.iat[idx],
                    pp_backend.net.bus.zone.iat[idx],
                    pp_backend.net.bus.type.iat[idx],
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


@dataclass(frozen=True)
class DataExportPsseBuses:
    number: list[int]
    name: list[str]
    bus_type: list[int]
    base_kv: list[float]
    voltage_pu: list[float]
    area_by_number: AreaByNumber
    area_number: list[int]
    zone_by_number: ZoneByNumber
    zone_number: list[int]


class DataExportBuses(GenericBuses[DataExportBus]):
    def __init__(self) -> None:
        super().__init__()
        self._psse_buses = DataExportPsseBuses(
            wf.abusint(string="number")[0],
            wf.abuschar(string="name")[0],
            wf.abusint(string="type")[0],
            wf.abusreal(string="kv")[0],
            wf.abusreal(string="pu")[0],
            AreaByNumber(),
            wf.abusint(string="area")[0],
            ZoneByNumber(),
            wf.abusint(string="zone")[0],
        )

    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[DataExportBus, tuple[DataExportBus, ...]]:
        if isinstance(idx, int):
            return DataExportBus(
                self._psse_buses.number[idx],
                self._psse_buses.name[idx],
                self._psse_buses.bus_type[idx],
                self._psse_buses.base_kv[idx],
                self._psse_buses.voltage_pu[idx],
                self._psse_buses.area_by_number[self._psse_buses.area_number[idx]],
                self._psse_buses.area_number[idx],
                self._psse_buses.zone_by_number[self._psse_buses.zone_number[idx]],
                self._psse_buses.zone_number[idx],
            )
        if isinstance(idx, slice):
            return tuple(
                DataExportBus(*args)
                for args in zip(
                    self._psse_buses.number[idx],
                    self._psse_buses.name[idx],
                    self._psse_buses.bus_type[idx],
                    self._psse_buses.base_kv[idx],
                    self._psse_buses.voltage_pu[idx],
                    self._psse_buses.area_by_number[self._psse_buses.area_number[idx]],
                    self._psse_buses.area_number[idx],
                    self._psse_buses.zone_by_number[self._psse_buses.zone_number[idx]],
                    self._psse_buses.zone_number[idx],
                )
            )
        raise RuntimeError(f"Wrong index {idx}")


class TemporaryBusLoad:
    TEMP_LOAD_ID: str = "Tm"

    def __init__(self, bus: Bus) -> None:
        self._bus: Bus = bus
        self._load_mva: complex

    def __enter__(self) -> None:
        self._bus.add_load(self._load_mva)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        # Delete load
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        self._bus.add_gen(self._gen_mva)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        # Delete machine
        if sys.platform == "win32" and not envs.pandapower_backend:
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
