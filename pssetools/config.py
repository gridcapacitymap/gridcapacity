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
import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, NonNegativeFloat, NonNegativeInt, PositiveInt

from pssetools.contingency_analysis import ContingencyScenario
from pssetools.violations_analysis import ViolationsLimits


class ConfigModel(BaseModel):
    case_name: str
    upper_load_limit_p_mw: NonNegativeFloat
    upper_gen_limit_p_mw: NonNegativeFloat
    load_power_factor: Optional[NonNegativeFloat] = 0.9
    gen_power_factor: Optional[NonNegativeFloat] = 0.9
    selected_buses_ids: Optional[list[NonNegativeInt]]
    solver_tolerance_p_mw: Optional[NonNegativeFloat] = 5.0
    solver_opts: Optional[dict] = {"options1": 1, "options5": 1}
    max_iterations: Optional[PositiveInt] = 10
    normal_limits: Optional[ViolationsLimits] = ViolationsLimits(
        max_bus_voltage_pu=1.1,
        min_bus_voltage_pu=0.9,
        max_branch_loading_pct=100.0,
        max_trafo_loading_pct=100.0,
        max_swing_bus_power_mva=1000.0,
        branch_rate="Rate1",
        trafo_rate="Rate1",
    )
    contingency_limits: Optional[ViolationsLimits] = ViolationsLimits(
        max_bus_voltage_pu=1.12,
        min_bus_voltage_pu=0.88,
        max_branch_loading_pct=120.0,
        max_trafo_loading_pct=120.0,
        max_swing_bus_power_mva=1000.0,
        branch_rate="Rate2",
        trafo_rate="Rate1",
    )
    contingency_scenario: Optional[ContingencyScenario]


def load_config_model(config_file_name: str) -> ConfigModel:
    """
    :param config_file_name: an absolute path or a path relative to this repository root
    :return: parsed config model
    """
    probably_absolute_path: Path = Path(config_file_name)
    config_file_path: Path = (
        probably_absolute_path
        if probably_absolute_path.is_absolute()
        else Path(__name__).absolute().parents[1] / config_file_name
    )
    return ConfigModel(**json.load(config_file_path.open(encoding="utf-8")))
