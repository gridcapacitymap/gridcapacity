from dataclasses import dataclass
from typing import Callable, Final, Iterator

from pssetools import wrapped_funcs as wf


@dataclass(frozen=True)
class Bus:
    number: int
    ex_name: str


@dataclass
class RawBuses:
    number: list[int]
    ex_name: list[str]


class Buses:
    def __init__(self) -> None:
        self._raw_buses: RawBuses = RawBuses(
            wf.abusint(string="number")[0],
            wf.abuschar(string="exName")[0],
        )

    def __iter__(self) -> Iterator[Bus]:
        for bus_idx in range(len(self)):
            yield Bus(
                self._raw_buses.number[bus_idx],
                self._raw_buses.ex_name[bus_idx],
            )

    def __len__(self) -> int:
        return len(self._raw_buses.number)


@dataclass
class Load:
    number: int
    ex_name: str
    load_id: str
    _mva_act: complex

    def __enter__(self) -> None:
        self._original_mva_act = self.mva_act

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.mva_act != self._original_mva_act:
            self.mva_act = self._original_mva_act
        del self._original_mva_act

    def __hash__(self):
        return hash((self.number, self.ex_name, self.load_id))

    @property
    def mva_act(self) -> complex:
        return self._mva_act

    @mva_act.setter
    def mva_act(self, mva_act: complex) -> None:
        if not hasattr(self, "_original_mva_act"):
            raise RuntimeError(
                "Load modification without context manager is prohibited. "
                "Use `with load:`."
            )
        wf.load_chng_6(self.number, self.load_id, realar=[mva_act.real, mva_act.imag])
        self._mva_act = mva_act

    def set_additional_load(self, additional_load: complex) -> None:
        self.mva_act = self._original_mva_act + additional_load


@dataclass
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
