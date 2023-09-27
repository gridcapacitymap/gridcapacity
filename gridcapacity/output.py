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
"""
import dataclasses
import json
from pathlib import Path
from typing import Any

import numpy as np
import rich

from gridcapacity.backends.subsystems import (
    DataExportBranch,
    DataExportBus,
    DataExportLoad,
    DataExportMachine,
    DataExportTrafo,
    DataExportTrafo3w,
)
from gridcapacity.capacity_analysis import CapacityAnalysisStats, Headroom
from gridcapacity.violations_analysis import Violations, ViolationsStats


def write_headroom_output(case_name: str, headroom: Headroom) -> None:
    case_path: Path = Path(case_name)
    output_folder = get_output_folder(case_path)
    output_file_prefix = case_path.stem
    headroom_output: Path = output_folder / f"{output_file_prefix}_headroom.json"
    violation_stats_output: Path = (
        output_folder / f"{output_file_prefix}_violation_stats.json"
    )
    contingency_stats_output: Path = output_folder / (
        f"{output_file_prefix}_contingency_stats.json"
    )
    feasibility_stats_output: Path = output_folder / (
        f"{output_file_prefix}_feasibility_stats.json"
    )
    json.dump(
        {"headroom": headroom},
        headroom_output.open("w", encoding="utf-8"),
        **json_dump_kwargs,
    )
    json.dump(
        {str(k): v for k, v in ViolationsStats.asdict().items()},
        violation_stats_output.open("w", encoding="utf-8"),
        **json_dump_kwargs,
    )
    json.dump(
        {
            "contingency_stats": tuple(
                {
                    "contingency": contingency,
                    "bus_contingency_conditions": tuple(
                        {"b": bus, "cc": contingency_condition}
                        for bus, contingency_condition in bus_to_contingency_conditions.items()
                    ),
                }
                for contingency, bus_to_contingency_conditions in CapacityAnalysisStats.contingencies_dict().items()
            )
        },
        contingency_stats_output.open("w", encoding="utf-8"),
        **json_dump_kwargs,
    )
    json.dump(
        {
            "feasibility_stats": tuple(
                {
                    "bus": bus,
                    "unfeasible_conditions": unfeasible_conditions,
                }
                for bus, unfeasible_conditions in CapacityAnalysisStats.feasibility_dict().items()
            )
        },
        feasibility_stats_output.open("w", encoding="utf-8"),
        **json_dump_kwargs,
    )
    rich.print(f'Headroom was written to "{headroom_output}"')


@dataclasses.dataclass
class ExportedData:
    buses: tuple[DataExportBus, ...]
    branches: tuple[DataExportBranch, ...]
    trafos: tuple[DataExportTrafo, ...]
    trafos3w: tuple[DataExportTrafo3w, ...]
    loads: tuple[DataExportLoad, ...]
    gens: tuple[DataExportMachine, ...]


def write_exported_data(case_name: str, exported_data: ExportedData) -> None:
    case_path: Path = Path(case_name)
    output_folder = get_output_folder(case_path)
    output_file_prefix = case_path.stem
    exported_data_path: Path = (
        output_folder / f"{output_file_prefix}_exported_data.json"
    )
    json.dump(
        exported_data,
        exported_data_path.open("w", encoding="utf-8"),
        **json_dump_kwargs,
    )
    rich.print(f'Exported data was written to "{exported_data_path}"')


def get_output_folder(case_path: Path) -> Path:
    if case_path.is_absolute():
        return case_path if case_path.is_dir() else case_path.parent
    else:
        return Path(__file__).absolute().parents[1]


def json_encode_helper(obj: Any) -> Any:
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    if isinstance(obj, Violations):
        return str(obj)
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)

    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()

    raise TypeError(f"{obj=} is not serializable")


json_dump_kwargs: dict = {
    "indent": 2,
    "default": json_encode_helper,
}
