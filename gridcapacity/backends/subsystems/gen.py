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
import logging
import sys
from abc import abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Generic, TypeVar

from ...envs import envs
from .area import AreaByNumber
from .utils import Printable
from .zone import ZoneByNumber

if sys.platform == "win32" and not envs.pandapower_backend:
    import psspy

    from ..psse import wrapped_funcs as wf
else:
    from .. import pandapower as pp_backend

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Machine:
    number: int
    ex_name: str
    machine_id: str
    pq_gen: complex


@dataclass(frozen=True)
class DataExportMachine:
    number: int
    name: str
    machine_id: str
    area_name: str
    area_number: int
    zone_name: str
    zone_number: int
    in_service: bool
    pq_gen: complex


@dataclass(frozen=True)
class PsseMachines:
    number: list[int]
    ex_name: list[str]
    machine_id: list[str]
    pq_gen: list[complex]


@dataclass(frozen=True)
class DataExportPsseMachines:
    number: list[int]
    name: list[str]
    machine_id: list[str]
    area_by_number: AreaByNumber
    area_number: tuple[int]
    zone_by_number: ZoneByNumber
    zone_number: tuple[int]
    status: list[int]
    pq_gen: list[complex]


GenericMachine = TypeVar("GenericMachine", Machine, DataExportMachine)
GenericPsseMachines = TypeVar(
    "GenericPsseMachines", PsseMachines, DataExportPsseMachines
)


class GenericMachines(Printable, Generic[GenericMachine, GenericPsseMachines]):
    def __init__(self) -> None:
        if sys.platform == "win32" and not envs.pandapower_backend:
            self._raw_machines: GenericPsseMachines

    @abstractmethod
    def __iter__(self) -> Iterator[GenericMachine]:
        raise NotImplementedError()

    def __len__(self) -> int:
        if sys.platform == "win32" and not envs.pandapower_backend:
            return len(self._raw_machines.number)
        # PandaPower models the generator either as static or dynamic generator.
        # And dynamic generator may be converted to a static
        # in certain conditions under the hood. See the note in
        # https://pandapower.readthedocs.io/en/v2.13.1/elements/gen.html#result-parameters
        return len(pp_backend.net.sgen) + len(pp_backend.net.gen)


class Machines(GenericMachines[Machine, PsseMachines]):
    def __init__(self) -> None:
        super().__init__()
        if sys.platform == "win32" and not envs.pandapower_backend:
            self._raw_machines: PsseMachines = PsseMachines(
                wf.amachint(string="number")[0],
                wf.amachchar(string="exName")[0],
                wf.amachchar(string="id")[0],
                wf.amachcplx(string="pqGen")[0],
            )

    def __iter__(self) -> Iterator[Machine]:
        for machine_idx in range(len(self)):
            if sys.platform == "win32" and not envs.pandapower_backend:
                yield Machine(
                    self._raw_machines.number[machine_idx],
                    self._raw_machines.ex_name[machine_idx],
                    self._raw_machines.machine_id[machine_idx],
                    self._raw_machines.pq_gen[machine_idx],
                )
            else:
                if machine_idx < len(pp_backend.net.sgen):
                    yield Machine(
                        pp_backend.net.bus.name[pp_backend.net.sgen.bus[machine_idx]],
                        "",
                        pp_backend.net.sgen.name[machine_idx],
                        pp_backend.net.res_sgen.p_mw[machine_idx]
                        + 1j * pp_backend.net.res_sgen.q_mvar[machine_idx],
                    )
                else:
                    machine_idx -= len(pp_backend.net.sgen)
                    yield Machine(
                        pp_backend.net.bus.name[pp_backend.net.gen.bus[machine_idx]],
                        "",
                        pp_backend.net.gen.name[machine_idx],
                        pp_backend.net.res_gen.p_mw[machine_idx]
                        + 1j * pp_backend.net.res_gen.q_mvar[machine_idx],
                    )


class DataExportMachines(GenericMachines[DataExportMachine, DataExportPsseMachines]):
    def __init__(self) -> None:
        super().__init__()
        bus_numbers = wf.amachint(string="number")[0]
        self._raw_machines: DataExportPsseMachines = DataExportPsseMachines(
            bus_numbers,
            wf.amachchar(string="name")[0],
            wf.amachchar(string="id")[0],
            AreaByNumber(),
            tuple((wf.busint(bus_number, "AREA") for bus_number in bus_numbers)),
            ZoneByNumber(),
            tuple((wf.busint(bus_number, "ZONE") for bus_number in bus_numbers)),
            wf.amachint(string="status")[0],
            wf.amachcplx(string="pqGen")[0],
        )

    def __iter__(self) -> Iterator[DataExportMachine]:
        for idx in range(len(self)):
            yield DataExportMachine(
                self._raw_machines.number[idx],
                self._raw_machines.name[idx],
                self._raw_machines.machine_id[idx],
                self._raw_machines.area_by_number[self._raw_machines.area_number[idx]],
                self._raw_machines.area_number[idx],
                self._raw_machines.zone_by_number[self._raw_machines.zone_number[idx]],
                self._raw_machines.zone_number[idx],
                self._raw_machines.status[idx] != 0,
                self._raw_machines.pq_gen[idx],
            )
