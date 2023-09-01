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
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, Union, overload

from ...envs import envs
from .utils import Printable

if sys.platform == "win32" and not envs.pandapower_backend:
    import psspy

    from ..psse import wrapped_funcs as wf
else:
    from .. import pandapower as pp_backend

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Trafo:
    from_number: int
    to_number: int
    trafo_id: str = "1"

    def is_enabled(self) -> bool:
        """Return `True` if is enabled"""
        if sys.platform == "win32" and not envs.pandapower_backend:
            # Trafo status is available through the branches `brnint` API only.
            # It isn't available through the trafos `xfrint` API.
            status: int = wf.brnint(
                self.from_number, self.to_number, self.trafo_id, "STATUS"
            )
            return status != 0
        trafo_idx: int = self.pp_idx
        return pp_backend.net.trafo.in_service[trafo_idx]

    if sys.platform != "win32" or envs.pandapower_backend:

        @property
        def pp_idx(self) -> int:
            """Returns index in a PandaPower network."""
            for idx, trafo in pp_backend.net.trafo.iterrows():
                if (
                    trafo["lv_bus"] == self.from_number
                    and trafo["hv_bus"] == self.to_number
                ) or (
                    trafo["hv_bus"] == self.from_number
                    and trafo["lv_bus"] == self.to_number
                ):
                    return idx
            raise KeyError(f"{self} not found!")


@dataclass(frozen=True)
class DataExportTrafo:
    from_number: int
    to_number: int
    trafo_id: str
    in_service: bool


GenericTrafo = TypeVar("GenericTrafo", Trafo, DataExportTrafo)


class GenericTrafos(Sequence, Printable, Generic[GenericTrafo]):
    def __init__(self, rate: str = "Rate1") -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._rate: str = rate

    @overload
    def __getitem__(self, idx: int) -> GenericTrafo:
        ...

    @overload
    def __getitem__(self, idx: slice) -> tuple[GenericTrafo, ...]:
        ...

    @abstractmethod
    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[GenericTrafo, tuple[GenericTrafo, ...]]:
        raise NotImplementedError()

    def __len__(self) -> int:
        if sys.platform == "win32" and not envs.pandapower_backend:
            return len(self._raw_trafos.from_number)
        return len(pp_backend.net.trafo)

    def __iter__(self) -> Iterator[GenericTrafo]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        yield from (self[i] for i in range(len(self)))

    def get_overloaded_indexes(self, max_trafo_loading_pct: float) -> tuple[int, ...]:
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        if sys.platform == "win32" and not envs.pandapower_backend:
            return tuple(self._raw_trafos.pct_rate[idx] for idx in selected_indexes)
        return tuple(
            pp_backend.net.res_trafo.loading_percent.iat[idx]
            for idx in selected_indexes
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
                if sys.platform == "win32" and not envs.pandapower_backend:
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


@dataclass
class PsseTrafos:
    from_number: list[int]
    to_number: list[int]
    trafo_id: list[str]
    pct_rate: list[float]


class Trafos(GenericTrafos[Trafo]):
    def __init__(self, rate: str = "Rate1") -> None:
        super().__init__(rate)
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        if sys.platform == "win32" and not envs.pandapower_backend:
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
                    pp_backend.net.trafo.hv_bus.iat[idx],
                    pp_backend.net.trafo.lv_bus.iat[idx],
                    pp_backend.net.trafo.parallel.iat[idx],
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


@dataclass
class DataExportPsseTrafos:
    from_number: list[int]
    to_number: list[int]
    trafo_id: list[str]
    status: list[int]


class DataExportTrafos(GenericTrafos[DataExportTrafo]):
    def __init__(self) -> None:
        super().__init__()
        self._raw_trafos: DataExportPsseTrafos = DataExportPsseTrafos(
            wf.atrnint(string="fromNumber")[0],
            wf.atrnint(string="toNumber")[0],
            wf.atrnchar(string="id")[0],
            wf.atrnint(string="status")[0],
        )

    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[DataExportTrafo, tuple[DataExportTrafo, ...]]:
        if isinstance(idx, int):
            return DataExportTrafo(
                self._raw_trafos.from_number[idx],
                self._raw_trafos.to_number[idx],
                self._raw_trafos.trafo_id[idx],
                self._raw_trafos.status[idx] != 0,
            )
        if isinstance(idx, slice):
            return tuple(
                DataExportTrafo(*args)
                for args in zip(
                    self._raw_trafos.from_number[idx],
                    self._raw_trafos.to_number[idx],
                    self._raw_trafos.trafo_id[idx],
                    (status != 0 for status in self._raw_trafos.status[idx]),
                )
            )
        raise RuntimeError(f"Wrong index {idx}")


@contextmanager
def disable_trafo(trafo: Trafo) -> Iterator[bool]:
    is_disabled: bool = False
    if sys.platform == "win32" and not envs.pandapower_backend:
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
