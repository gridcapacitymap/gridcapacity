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
class Branch:
    from_number: int
    to_number: int
    branch_id: str = "1"

    def is_enabled(self) -> bool:
        """Return `True` if is enabled."""
        if sys.platform == "win32" and not envs.pandapower_backend:
            status: int = wf.brnint(
                self.from_number, self.to_number, self.branch_id, "STATUS"
            )
            return status != 0
        branch_idx: int = self.pp_idx
        return pp_backend.net.line.in_service[branch_idx]

    def disable(self) -> None:
        if sys.platform == "win32" and not envs.pandapower_backend:
            wf.branch_chng_3(self.from_number, self.to_number, self.branch_id, st=0)
            return
        branch_idx: int = self.pp_idx
        pp_backend.net.line.in_service[branch_idx] = False
        return

    if sys.platform != "win32" or envs.pandapower_backend:

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


@dataclass(frozen=True)
class DataExportBranch:
    from_number: int
    to_number: int
    branch_id: str
    in_service: bool


GenericBranch = TypeVar("GenericBranch", Branch, DataExportBranch)


class GenericBranches(Sequence, Printable, Generic[GenericBranch]):
    def __init__(self, rate: str = "Rate1") -> None:
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._rate: str = rate

    @overload
    def __getitem__(self, idx: int) -> GenericBranch:
        ...

    @overload
    def __getitem__(self, idx: slice) -> tuple[GenericBranch, ...]:
        ...

    @abstractmethod
    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[GenericBranch, tuple[GenericBranch, ...]]:
        raise NotImplementedError()

    def __len__(self) -> int:
        if sys.platform == "win32" and not envs.pandapower_backend:
            return len(self._psse_branches.from_number)
        return len(pp_backend.net.line)

    def __iter__(self) -> Iterator[Branch]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        yield from (self[i] for i in range(len(self)))

    def get_overloaded_indexes(self, max_branch_loading_pct: float) -> tuple[int, ...]:
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        if sys.platform == "win32" and not envs.pandapower_backend:
            return tuple(self._psse_branches.pct_rate[idx] for idx in selected_indexes)
        return tuple(
            pp_backend.net.res_line.loading_percent.iat[idx] for idx in selected_indexes
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
                if sys.platform == "win32" and not envs.pandapower_backend:
                    loading_pct = self._psse_branches.pct_rate[idx]
                else:
                    loading_pct = pp_backend.net.res_line.loading_percent.iat[idx]
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


@dataclass
class PsseBranches:
    from_number: list[int]
    to_number: list[int]
    branch_id: list[str]
    pct_rate: list[float]


class Branches(GenericBranches[Branch]):
    def __init__(self, rate: str = "Rate1") -> None:
        super().__init__(rate)
        if sys.platform == "win32" and not envs.pandapower_backend:
            self._psse_branches: PsseBranches = PsseBranches(
                wf.abrnint(string="fromNumber")[0],
                wf.abrnint(string="toNumber")[0],
                wf.abrnchar(string="id")[0],
                wf.abrnreal(string=f"pct{self._rate}")[0],
            )

    def __getitem__(self, idx: Union[int, slice]) -> Union[Branch, tuple[Branch, ...]]:
        if sys.platform == "win32" and not envs.pandapower_backend:
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
                    pp_backend.net.line.from_bus.iat[idx],
                    pp_backend.net.line.to_bus.iat[idx],
                    pp_backend.net.line.parallel.iat[idx],
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


@dataclass
class DataExportPsseBranches:
    from_number: list[int]
    to_number: list[int]
    branch_id: list[str]
    status: list[int]


class DataExportBranches(GenericBranches[DataExportBranch]):
    def __init__(self) -> None:
        super().__init__()
        self._psse_branches: DataExportPsseBranches = DataExportPsseBranches(
            wf.abrnint(string="fromNumber")[0],
            wf.abrnint(string="toNumber")[0],
            wf.abrnchar(string="id")[0],
            wf.abrnint(string="status")[0],
        )

    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[DataExportBranch, tuple[DataExportBranch, ...]]:
        if isinstance(idx, int):
            return DataExportBranch(
                self._psse_branches.from_number[idx],
                self._psse_branches.to_number[idx],
                self._psse_branches.branch_id[idx],
                self._psse_branches.status[idx] != 0,
            )
        if isinstance(idx, slice):
            return tuple(
                DataExportBranch(*args)
                for args in zip(
                    self._psse_branches.from_number[idx],
                    self._psse_branches.to_number[idx],
                    self._psse_branches.branch_id[idx],
                    (status != 0 for status in self._psse_branches.status[idx]),
                )
            )
        raise RuntimeError(f"Wrong index {idx}")


@contextmanager
def disable_branch(branch: Branch) -> Iterator[bool]:
    is_disabled: bool = False
    if sys.platform == "win32" and not envs.pandapower_backend:
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
