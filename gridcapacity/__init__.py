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
import logging
import sys

from rich.logging import RichHandler

from gridcapacity.capacity_analysis import CapacityAnalysisStats, buses_headroom
from gridcapacity.config import ConfigModel, load_config_model
from gridcapacity.console import console
from gridcapacity.envs import envs
from gridcapacity.output import write_headroom_output
from gridcapacity.violations_analysis import ViolationsStats


def build_headroom() -> None:
    logging_level: int = logging.WARNING if not envs.verbose else logging.DEBUG
    logging.basicConfig(
        level=logging_level,
        handlers=[RichHandler(rich_tracebacks=True, log_time_format="%X")],
    )
    if len(sys.argv) != 2:
        raise RuntimeError(
            f"Config file name should be specified "
            f"as a program argument. Got {sys.argv}"
        )
    config_file_name: str = sys.argv[1]
    config_model: ConfigModel = load_config_model(config_file_name)
    headroom = buses_headroom(**config_model.dict(exclude_unset=True))
    if headroom:
        write_headroom_output(config_model.case_name, headroom)
        CapacityAnalysisStats.print()
        console.rule("HEADROOM")
        for bus_headroom in headroom:
            console.print(bus_headroom)
        if not ViolationsStats.is_empty():
            console.rule("VIOLATIONS STATS")
            ViolationsStats.print()
        else:
            console.print("No violations detected", style="green")
        if not ViolationsStats.base_case_violations_detected():
            console.rule("[bold red]BASE CASE VIOLATIONS")
            ViolationsStats.print_base_case_violations()
        else:
            console.print("No base case violations detected", style="green")
    else:
        console.print("No headroom found", style="bold red")


if __name__ == "__main__":
    build_headroom()
