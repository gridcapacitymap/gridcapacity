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
class Load:
    number: int
    ex_name: str
    load_id: str
    mva_act: complex


@dataclass(frozen=True)
class DataExportLoad:
    number: int
    name: str
    load_id: str
    area_name: str
    area_number: int
    zone_name: str
    zone_number: int
    in_service: bool
    mva_act: complex


@dataclass(frozen=True)
class PsseLoads:
    number: list[int]
    ex_name: list[str]
    load_id: list[str]
    mva_act: list[complex]


@dataclass(frozen=True)
class DataExportPsseLoads:
    number: list[int]
    name: list[str]
    load_id: list[str]
    area_by_number: AreaByNumber
    area_number: list[int]
    zone_by_number: ZoneByNumber
    zone_number: list[int]
    status: list[int]
    mva_act: list[complex]


GenericLoad = TypeVar("GenericLoad", Load, DataExportLoad)
GenericPsseLoads = TypeVar("GenericPsseLoads", PsseLoads, DataExportPsseLoads)


class GenericLoads(Printable, Generic[GenericLoad, GenericPsseLoads]):
    def __init__(self) -> None:
        if sys.platform == "win32" and not envs.pandapower_backend:
            self._raw_loads: GenericPsseLoads

    @abstractmethod
    def __iter__(self) -> Iterator[GenericLoad]:
        raise NotImplementedError()

    def __len__(self) -> int:
        if sys.platform == "win32" and not envs.pandapower_backend:
            return len(self._raw_loads.number)
        return len(pp_backend.net.load)


class Loads(GenericLoads[Load, PsseLoads]):
    def __init__(self) -> None:
        super().__init__()
        if sys.platform == "win32" and not envs.pandapower_backend:
            self._raw_loads: PsseLoads = PsseLoads(
                wf.aloadint(string="number")[0],
                wf.aloadchar(string="exName")[0],
                wf.aloadchar(string="id")[0],
                wf.aloadcplx(string="mvaAct")[0],
            )

    def __iter__(self) -> Iterator[Load]:
        for load_idx in range(len(self)):
            if sys.platform == "win32" and not envs.pandapower_backend:
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


class DataExportLoads(GenericLoads[DataExportLoad, DataExportPsseLoads]):
    def __init__(self) -> None:
        super().__init__()
        self._raw_loads: DataExportPsseLoads = DataExportPsseLoads(
            wf.aloadint(string="number")[0],
            wf.aloadchar(string="name")[0],
            wf.aloadchar(string="id")[0],
            AreaByNumber(),
            wf.aloadint(string="area")[0],
            ZoneByNumber(),
            wf.aloadint(string="zone")[0],
            wf.aloadint(string="status")[0],
            wf.aloadcplx(string="mvaAct")[0],
        )

    def __iter__(self) -> Iterator[DataExportLoad]:
        for idx in range(len(self)):
            yield DataExportLoad(
                self._raw_loads.number[idx],
                self._raw_loads.name[idx],
                self._raw_loads.load_id[idx],
                self._raw_loads.area_by_number[self._raw_loads.area_number[idx]],
                self._raw_loads.area_number[idx],
                self._raw_loads.zone_by_number[self._raw_loads.zone_number[idx]],
                self._raw_loads.zone_number[idx],
                self._raw_loads.status[idx] != 0,
                self._raw_loads.mva_act[idx],
            )
