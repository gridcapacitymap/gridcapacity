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

from pssetools import CapacityAnalysisStats
from pssetools.capacity_analysis import Headroom
from pssetools.violations_analysis import Violations, ViolationsStats


def write_output(case_name: str, headroom: Headroom) -> None:
    case_path: Path = Path(case_name)
    output_folder: Path = (
        case_path if case_path.is_absolute() else Path(__file__).absolute().parents[1]
    )
    output_file_prefix: str = case_name.removesuffix(case_path.suffix)
    headroom_output: Path = output_folder / (output_file_prefix + "_headroom.json")
    violation_stats_output: Path = output_folder / (
        output_file_prefix + "_violation_stats.json"
    )
    contingency_stats_output: Path = output_folder / (
        output_file_prefix + "_contingency_stats.json"
    )
    feasibility_stats_output: Path = output_folder / (
        output_file_prefix + "_feasibility_stats.json"
    )
    json_dump_kwargs: dict = {
        "indent": 2,
        "default": json_encode_helper,
    }
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
    print(f'Headroom was written to "{headroom_output}"')


def json_encode_helper(obj: Any) -> Any:
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    elif isinstance(obj, Violations):
        return str(obj)
    elif dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    else:
        raise TypeError(f"{obj=} is not serializable")
