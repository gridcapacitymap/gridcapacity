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

Script exports a PSSE case to a JSON file
"""
from dataclasses import dataclass

import rich
import typer

from gridcapacity.backends import wrapped_funcs as wf
from gridcapacity.backends.subsystems import (
    DataExportBranches,
    DataExportBuses,
    DataExportLoads,
    DataExportMachines,
    DataExportTrafos,
    DataExportTrafos3w,
)
from gridcapacity.output import ExportedData, write_exported_data


@dataclass(frozen=True)
class BusModel:
    number: int
    ex_name: str
    type: int


def convert_case2json(case_name: str) -> None:
    wf.open_case(case_name)
    buses = DataExportBuses()
    for bus in buses:
        rich.print(bus)
    branches = DataExportBranches()
    for branch in branches:
        rich.print(branch)
    trafos = DataExportTrafos()
    for trafo in trafos:
        rich.print(trafo)
    trafos3w = DataExportTrafos3w()
    for trafo3w in trafos3w:
        rich.print(trafo3w)
    loads = DataExportLoads()
    for load in loads:
        rich.print(load)
    gens = DataExportMachines()
    for gen in gens:
        rich.print(gen)
    write_exported_data(
        case_name,
        ExportedData(
            tuple(bus for bus in buses),
            tuple(branch for branch in branches),
            tuple(trafo for trafo in trafos),
            tuple(trafo3w for trafo3w in trafos3w),
            tuple(load for load in loads),
            tuple(gen for gen in gens),
        ),
    )


if __name__ == "__main__":
    typer.run(convert_case2json)
