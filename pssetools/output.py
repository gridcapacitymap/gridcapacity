import dataclasses
import json
from pathlib import Path
from typing import Any

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
    json_dump_kwargs: dict = {
        "indent": 2,
        "default": json_encode_helper,
    }
    json.dump(
        {
            "headroom": tuple(
                dataclasses.asdict(bus_headroom) for bus_headroom in headroom
            )
        },
        headroom_output.open("w", encoding="utf-8"),
        **json_dump_kwargs,
    )
    json.dump(
        {str(k): v for k, v in ViolationsStats.asdict().items()},
        violation_stats_output.open("w", encoding="utf-8"),
        **json_dump_kwargs,
    )
    print(f'Output was written to "{headroom_output}" and "{violation_stats_output}"')


def json_encode_helper(obj: Any) -> Any:
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    elif isinstance(obj, Violations):
        return str(obj)
    else:
        raise TypeError(f"{obj=} is not serializable")
