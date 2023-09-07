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
class Trafo3w:
    wind1_number: int
    wind2_number: int
    wind3_number: int
    trafo_id: str

    def is_enabled(self) -> bool:
        """Return `True` if is enabled"""
        if sys.platform == "win32" and not envs.pandapower_backend:
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


@dataclass(frozen=True)
class DataExportTrafo3w:
    wind1_number: int
    wind2_number: int
    wind3_number: int
    trafo_id: str
    in_service: bool


GenericTrafo3w = TypeVar("GenericTrafo3w", Trafo3w, DataExportTrafo3w)


class GenericTrafos3w(Sequence, Printable, Generic[GenericTrafo3w]):
    def __init__(self, rate: str = "Rate1") -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._rate: str = rate
        if sys.platform == "win32" and not envs.pandapower_backend:
            self._raw_trafos: PsseTrafos3w = PsseTrafos3w(
                wf.awndint(string="wind1Number")[0],
                wf.awndint(string="wind2Number")[0],
                wf.awndint(string="wind3Number")[0],
                wf.awndchar(string="id")[0],
                wf.awndreal(string=f"pct{self._rate}")[0],
            )

    @overload
    def __getitem__(self, idx: int) -> GenericTrafo3w:
        ...

    @overload
    def __getitem__(self, idx: slice) -> tuple[GenericTrafo3w, ...]:
        ...

    @abstractmethod
    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[GenericTrafo3w, tuple[GenericTrafo3w, ...]]:
        raise NotImplementedError()

    def __len__(self) -> int:
        if sys.platform == "win32" and not envs.pandapower_backend:
            return len(self._raw_trafos.wind1_number)
        return len(pp_backend.net.trafo3w)

    def __iter__(self) -> Iterator[GenericTrafo3w]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        yield from (self[i] for i in range(len(self)))

    def get_overloaded_indexes(self, max_trafo_loading_pct: float) -> tuple[int, ...]:
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        if sys.platform == "win32" and not envs.pandapower_backend:
            return tuple(self._raw_trafos.pct_rate[idx] for idx in selected_indexes)
        return tuple(
            pp_backend.net.res_trafo3w.loading_percent.iat[idx]
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
                    loadings_pct = self._raw_trafos.pct_rate[idx]
                else:
                    loadings_pct = pp_backend.net.res_trafo3w.loading_percent.iat[idx]
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


@dataclass
class PsseTrafos3w:
    wind1_number: list[int]
    wind2_number: list[int]
    wind3_number: list[int]
    trafo_id: list[str]
    pct_rate: list[float]


class Trafos3w(GenericTrafos3w[Trafo3w]):
    def __init__(self, rate: str = "Rate1") -> None:
        super().__init__(rate)
        if sys.platform == "win32" and not envs.pandapower_backend:
            self._raw_trafos: PsseTrafos3w = PsseTrafos3w(
                wf.awndint(string="wind1Number")[0],
                wf.awndint(string="wind2Number")[0],
                wf.awndint(string="wind3Number")[0],
                wf.awndchar(string="id")[0],
                wf.awndreal(string=f"pct{self._rate}")[0],
            )

    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[Trafo3w, tuple[Trafo3w, ...]]:
        if sys.platform == "win32" and not envs.pandapower_backend:
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
                    pp_backend.net.trafo3w.hv_bus.iat[idx],
                    pp_backend.net.trafo3w.mv_bus.iat[idx],
                    pp_backend.net.trafo3w.lv_bus.iat[idx],
                    pp_backend.net.trafo3w.parallel.iat[idx],
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


@dataclass
class DataExportPsseTrafos3w:
    wind1_number: list[int]
    wind2_number: list[int]
    wind3_number: list[int]
    trafo_id: list[str]
    status: list[int]


class DataExportTrafos3w(GenericTrafos3w[DataExportTrafo3w]):
    def __init__(self) -> None:
        super().__init__()
        self._raw_trafos: DataExportPsseTrafos3w = DataExportPsseTrafos3w(
            wf.awndint(string="wind1Number")[0],
            wf.awndint(string="wind2Number")[0],
            wf.awndint(string="wind3Number")[0],
            wf.awndchar(string="id")[0],
            wf.awndint(string="status")[0],
        )

    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[DataExportTrafo3w, tuple[DataExportTrafo3w, ...]]:
        if isinstance(idx, int):
            return DataExportTrafo3w(
                self._raw_trafos.wind1_number[idx],
                self._raw_trafos.wind2_number[idx],
                self._raw_trafos.wind3_number[idx],
                self._raw_trafos.trafo_id[idx],
                self._raw_trafos.status[idx] != 0,
            )
        if isinstance(idx, slice):
            return tuple(
                DataExportTrafo3w(*args)
                for args in zip(
                    self._raw_trafos.wind1_number[idx],
                    self._raw_trafos.wind2_number[idx],
                    self._raw_trafos.wind3_number[idx],
                    self._raw_trafos.trafo_id[idx],
                    (status != 0 for status in self._raw_trafos.status[idx]),
                )
            )
        raise RuntimeError(f"Wrong index {idx}")
