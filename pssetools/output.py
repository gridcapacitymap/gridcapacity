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
        case_path if case_path.is_absolute() else Path(__name__).absolute().parents[1]
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
                    "violations_by_bus": tuple(
                        {"b": bus, "vv": violations}
                        for bus, violations in bus_to_contingency_violation.items()
                    ),
                }
                for contingency, bus_to_contingency_violation in CapacityAnalysisStats.contingencies_dict().items()
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
                    "violations": violations,
                }
                for bus, violations in CapacityAnalysisStats.feasibility_dict().items()
            )
        },
        feasibility_stats_output.open("w", encoding="utf-8"),
        **json_dump_kwargs,
    )
    print(f'Output was written to "{headroom_output}" and "{violation_stats_output}"')


def json_encode_helper(obj: Any) -> Any:
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    elif isinstance(obj, Violations):
        return str(obj)
    elif dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    else:
        raise TypeError(f"{obj=} is not serializable")
