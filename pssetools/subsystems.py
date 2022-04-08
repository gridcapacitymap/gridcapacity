from dataclasses import dataclass
from typing import Callable, Final, Iterator

from pssetools import wrapped_funcs as wf


@dataclass
class Load:
    number: int
    ex_name: str
    load_id: str
    mva_act: complex


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
        for load_idx in range(len(self._raw_loads.number)):
            yield Load(
                self._raw_loads.number[load_idx],
                self._raw_loads.ex_name[load_idx],
                self._raw_loads.load_id[load_idx],
                self._raw_loads.mva_act[load_idx],
            )
