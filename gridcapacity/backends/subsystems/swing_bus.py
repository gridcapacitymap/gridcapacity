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
from dataclasses import dataclass
from typing import Final, Iterator, Optional, Sequence, Union, overload

from ...envs import envs
from .utils import Printable

if sys.platform == "win32" and not envs.pandapower_backend:
    import psspy

    from ..psse import wrapped_funcs as wf
else:
    from .. import pandapower as pp_backend

log = logging.getLogger(__name__)


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
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        if sys.platform == "win32" and not envs.pandapower_backend:
            return len(self._raw_buses.number)
        return len(pp_backend.net.ext_grid)

    def __iter__(self) -> Iterator[SwingBus]:
        """Override Sequence `iter` method because PandaPower throws `KeyError` where `IndexError` is expected."""
        for i in range(len(self)):
            yield self[i]

    def get_overloaded_indexes(
        self, max_swing_bus_power_p_mw: float
    ) -> tuple[int, ...]:
        if sys.platform == "win32" and not envs.pandapower_backend:
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
        if sys.platform == "win32" and not envs.pandapower_backend:
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
                if sys.platform == "win32" and not envs.pandapower_backend:
                    p_mw = self._raw_buses.pgen[idx]
                else:
                    p_mw = pp_backend.net.res_ext_grid.p_mw[idx]
                self._log.log(
                    level,
                    tuple((*dataclasses.astuple(bus), p_mw)),
                )
        self._log.log(level, bus_fields)
