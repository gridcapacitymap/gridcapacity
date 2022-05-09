import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Extra, NonNegativeFloat, NonNegativeInt, PositiveInt

from pssetools.contingency_analysis import ContingencyScenario
from pssetools.violations_analysis import ViolationsLimits


class ConfigModel(BaseModel):  # , extra=Extra.forbid):
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
    )
    contingency_limits: Optional[ViolationsLimits] = ViolationsLimits(
        max_bus_voltage_pu=1.12,
        min_bus_voltage_pu=0.88,
        max_branch_loading_pct=120.0,
        max_trafo_loading_pct=120.0,
        max_swing_bus_power_mva=1000.0,
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
    return ConfigModel(**json.load(open(config_file_path, encoding="utf-8")))
