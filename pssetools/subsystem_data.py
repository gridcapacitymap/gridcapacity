"""Functions that retrieve data using the API functions described in the Chapter 12
"Subsystem Data Retrieval" of the PSSE 35 API.
"""
import logging
import os
from typing import Callable, Final, Optional, Union

from pssetools import wrapped_funcs as wf

log = logging.getLogger(__name__)
LOG_LEVEL: Final[int] = (
    logging.INFO
    if not os.getenv("PSSE_TOOLS_TREAT_VIOLATIONS_AS_WARNINGS")
    else logging.WARNING
)
field_type2func_suffix: Final[dict[str, str]] = {
    "I": "int",
    "R": "real",
    "X": "cplx",
    "C": "char",
}
FieldType = Union[int, float, complex, str]

SWING_BUS: Final[int] = 3


def get_branch_field(field_name: str) -> list[FieldType]:
    field_type = wf.abrntypes(string=field_name)[0]
    api_func: Callable = getattr(wf, f"abrn{field_type2func_suffix[field_type]}")
    value = api_func(string=field_name)[0]
    return value


def get_bus_field(field_name: str) -> list[FieldType]:
    field_type = wf.abustypes(string=field_name)[0]
    api_func: Callable = getattr(wf, f"abus{field_type2func_suffix[field_type]}")
    value = api_func(string=field_name)[0]
    return value


def get_load_field(field_name: str) -> list[FieldType]:
    field_type = wf.aloadtypes(string=field_name)[0]
    api_func: Callable = getattr(wf, f"aload{field_type2func_suffix[field_type]}")
    value = api_func(string=field_name)[0]
    return value


def get_plant_bus_field(field_name: str) -> list[FieldType]:
    field_type = wf.agenbustypes(string=field_name)[0]
    api_func: Callable = getattr(wf, f"agenbus{field_type2func_suffix[field_type]}")
    value = api_func(string=field_name)[0]
    return value


def get_trafo_field(field_name: str) -> list[FieldType]:
    field_type = wf.atrntypes(string=field_name)[0]
    api_func: Callable = getattr(wf, f"atrn{field_type2func_suffix[field_type]}")
    value = api_func(string=field_name)[0]
    return value


def get_trafo_3w_field(field_name: str) -> list[FieldType]:
    field_type = wf.awndtypes(string=field_name)[0]
    api_func: Callable = getattr(wf, f"awnd{field_type2func_suffix[field_type]}")
    value = api_func(string=field_name)[0]
    return value


def get_overloaded_branches_ids(max_branch_loading_pct: float) -> tuple[int, ...]:
    """Check `Percent from bus current of rating set 1`"""
    ids: tuple[int, ...] = tuple(
        branch_id
        for branch_id, pct_rate1 in enumerate(wf.abrnreal(string="pctRate1")[0])
        if pct_rate1 > max_branch_loading_pct
    )
    return ids


def get_overloaded_swing_buses_ids(max_swing_bus_power_mva: float) -> tuple[int, ...]:
    ids: tuple[int, ...] = tuple(
        bus_id
        for bus_id, (bus_type, mva) in enumerate(
            zip(wf.agenbusint(string="type")[0], wf.agenbusreal(string="mva")[0])
        )
        if bus_type == SWING_BUS and mva > max_swing_bus_power_mva
    )
    return ids


def get_overloaded_trafos_3w_ids(max_trafo_3w_loading_pct: float) -> tuple[int, ...]:
    """Check `Percent from bus current of rating set 1`"""
    ids: tuple[int, ...] = tuple(
        trafo_3w_id
        for trafo_3w_id, pct_rate1 in enumerate(wf.awndreal(string="pctRate1")[0])
        if pct_rate1 > max_trafo_3w_loading_pct
    )
    return ids


def get_overloaded_trafos_ids(max_trafo_loading_pct: float) -> tuple[int, ...]:
    """Check `Percent from bus current of rating set 1`"""
    ids: tuple[int, ...] = tuple(
        trafo_id
        for trafo_id, pct_rate1 in enumerate(wf.atrnreal(string="pctRate1")[0])
        if pct_rate1 > max_trafo_loading_pct
    )
    return ids


def get_overvoltage_buses_ids(max_bus_voltage: float) -> tuple[int, ...]:
    ids: tuple[int, ...] = tuple(
        bus_id
        for bus_id, pu_voltage in enumerate(wf.abusreal(string="pu")[0])
        if pu_voltage > max_bus_voltage
    )
    return ids


def get_undervoltage_buses_ids(min_bus_voltage: float) -> tuple[int, ...]:
    ids: tuple[int, ...] = tuple(
        bus_id
        for bus_id, pu_voltage in enumerate(wf.abusreal(string="pu")[0])
        if pu_voltage < min_bus_voltage
    )
    return ids


def print_branches(
    selected_ids: Optional[tuple[int, ...]] = None,
    branch_fields: tuple[str, ...] = (
        "fromNumber",
        "fromName",
        "toNumber",
        "toName",
        "id",
        "pq",
        "mva",
        "rate1",
        "pctRate1",
    ),
) -> None:
    values: tuple[list[FieldType], ...] = tuple(
        get_branch_field(field_name) for field_name in branch_fields
    )

    log.log(LOG_LEVEL, branch_fields)
    for row in range(len(values[0])):
        if selected_ids is None or row in selected_ids:
            log.log(LOG_LEVEL, tuple(values[col][row] for col in range(len(values))))
    log.log(LOG_LEVEL, branch_fields)


def print_buses(
    selected_ids: Optional[tuple[int, ...]] = None,
    bus_fields: tuple[str, ...] = (
        "number",
        "name",
        "base",
        "pu",
        "angleD",
        "nVLmHi",
        "nVLmLo",
    ),
) -> None:
    values: tuple[list[FieldType], ...] = tuple(
        get_bus_field(field_name) for field_name in bus_fields
    )

    log.log(LOG_LEVEL, bus_fields)
    for row in range(len(values[0])):
        if selected_ids is None or row in selected_ids:
            log.log(LOG_LEVEL, tuple(values[col][row] for col in range(len(values))))
    log.log(LOG_LEVEL, bus_fields)


def print_loads(
    selected_ids: Optional[tuple[int, ...]] = None,
    load_fields: tuple[str, ...] = (
        "number",
        "exName",
        "id",
        "mvaAct",
    ),
) -> None:
    values: tuple[list[FieldType], ...] = tuple(
        get_load_field(field_name) for field_name in load_fields
    )

    log.log(LOG_LEVEL, load_fields)
    for row in range(len(values[0])):
        if selected_ids is None or row in selected_ids:
            log.log(LOG_LEVEL, tuple(values[col][row] for col in range(len(values))))
    log.log(LOG_LEVEL, load_fields)


def print_swing_buses(
    selected_ids: Optional[tuple[int, ...]] = None,
    plant_bus_fields: tuple[str, ...] = (
        "number",
        "exName",
        "mva",
        "pqGen",
    ),
) -> None:
    values: tuple[list[FieldType], ...] = tuple(
        get_plant_bus_field(field_name) for field_name in plant_bus_fields
    )
    buses_types: list[int] = wf.agenbusint(string="type")[0]

    log.log(LOG_LEVEL, plant_bus_fields)
    for row, bus_type in zip(range(len(values[0])), buses_types):
        if bus_type == SWING_BUS and (selected_ids is None or row in selected_ids):
            log.log(LOG_LEVEL, tuple(values[col][row] for col in range(len(values))))
    log.log(LOG_LEVEL, plant_bus_fields)


def print_trafos(
    selected_ids: Optional[tuple[int, ...]] = None,
    trafo_fields: tuple[str, ...] = (
        "fromNumber",
        "fromExName",
        "toNumber",
        "toExName",
        "id",
        "pq",
        "mva",
        "rate1",
        "pctRate1",
    ),
) -> None:
    values: tuple[list[FieldType], ...] = tuple(
        get_trafo_field(field_name) for field_name in trafo_fields
    )

    log.log(LOG_LEVEL, trafo_fields)
    for row in range(len(values[0])):
        if selected_ids is None or row in selected_ids:
            log.log(LOG_LEVEL, tuple(values[col][row] for col in range(len(values))))
    log.log(LOG_LEVEL, trafo_fields)


def print_trafos_3w(
    selected_ids: Optional[tuple[int, ...]] = None,
    trafo_3w_fields: tuple[str, ...] = (
        "wind1Number",
        "wind1ExName",
        "wind2Number",
        "wind2ExName",
        "wind3Number",
        "wind3ExName",
        "id",
        "pq",
        "mva",
        "rate1",
        "pctRate1",
    ),
) -> None:
    values: tuple[list[FieldType], ...] = tuple(
        get_trafo_3w_field(field_name) for field_name in trafo_3w_fields
    )

    log.log(LOG_LEVEL, trafo_3w_fields)
    for row in range(len(values[0])):
        if selected_ids is None or row in selected_ids:
            log.log(LOG_LEVEL, tuple(values[col][row] for col in range(len(values))))
    log.log(LOG_LEVEL, trafo_3w_fields)
