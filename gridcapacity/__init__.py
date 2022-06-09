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
import os
import sys

from gridcapacity.backends import wrapped_funcs as wf

# from pssetools.config import ConfigModel, load_config_model
# from pssetools.capacity_analysis import CapacityAnalysisStats, buses_headroom
# from pssetools.output import write_output
# from pssetools.violations_analysis import ViolationsLimits, ViolationsStats


def build_headroom() -> None:
    logging_level: int = (
        logging.WARNING
        if not os.environ.get("GRID_CAPACITY_VERBOSE")
        else logging.DEBUG
    )
    logging.basicConfig(level=logging_level)
    if len(sys.argv) != 2:
        raise RuntimeError(
            f"Config file name should be specified "
            f"as a program argument. Got {sys.argv}"
        )
    config_file_name: str = sys.argv[1]
    wf.open_case(config_file_name)
    wf.run_solver(use_full_newton_raphson=False)
    # config_model: ConfigModel = load_config_model(config_file_name)
    # headroom = buses_headroom(**config_model.dict(exclude_unset=True))
    # if len(headroom):
    #     write_output(config_model.case_name, headroom)
    #     CapacityAnalysisStats.print()
    #     print()
    #     print(" HEADROOM ".center(80, "="))
    #     for bus_headroom in headroom:
    #         print(bus_headroom)
    #     if not ViolationsStats.is_empty():
    #         print()
    #         print(" VIOLATIONS STATS ".center(80, "="))
    #         ViolationsStats.print()
    #     else:
    #         print("No violations detected")
    # else:
    #     print("No headroom found")


if __name__ == "__main__":
    build_headroom()
