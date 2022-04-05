"""Functions that retrieve data using the API functions described in the Chapter 12
"Subsystem Data Retrieval" of the PSSE 35 API.
"""
from typing import Callable, Final, Optional, Union

from pssetools import wrapped_funcs as wf

field_type2func_suffix: Final[dict[str, str]] = {
    "I": "int",
    "R": "real",
    "X": "cplx",
    "C": "char",
}
FieldType = Union[int, float, complex, str]


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


def get_trafo_field(field_name: str) -> list[FieldType]:
    field_type = wf.atrntypes(string=field_name)[0]
    api_func: Callable = getattr(wf, f"atrn{field_type2func_suffix[field_type]}")
    value = api_func(string=field_name)[0]
    return value


def get_overloaded_branches_ids(max_branch_loading_pct: float) -> tuple[int]:
    """Check `Percent from bus current of rating set 1`"""
    ids: tuple[int] = tuple(
        branch_id
        for branch_id, pct_rate1 in enumerate(get_branch_field("pctRate1"))
        if pct_rate1 > max_branch_loading_pct
    )
    return ids


def get_overloaded_trafos_ids(max_trafo_loading_pct: float) -> tuple[int]:
    """Check `Percent from bus current of rating set 1`"""
    ids: tuple[int] = tuple(
        trafo_id
        for trafo_id, pct_rate1 in enumerate(get_trafo_field("pctRate1"))
        if pct_rate1 > max_trafo_loading_pct
    )
    return ids


def get_overvoltage_buses_ids(max_bus_voltage: float) -> tuple[int]:
    ids: tuple[int] = tuple(
        bus_id
        for bus_id, pu_voltage in enumerate(get_bus_field("pu"))
        if pu_voltage > max_bus_voltage
    )
    return ids


def get_undervoltage_buses_ids(min_bus_voltage: float) -> tuple[int]:
    ids: tuple[int] = tuple(
        bus_id
        for bus_id, pu_voltage in enumerate(get_bus_field("pu"))
        if pu_voltage < min_bus_voltage
    )
    return ids


def print_branches(
    selected_ids: Optional[tuple[int]] = None,
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
):
    values: tuple[list[FieldType]] = tuple(
        get_branch_field(field_name) for field_name in branch_fields
    )

    print(branch_fields)
    for row in range(len(values[0])):
        if selected_ids is None or row in selected_ids:
            print(tuple(values[col][row] for col in range(len(values))))
    print(branch_fields)


def print_trafos(
    selected_ids: Optional[tuple[int]] = None,
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
):
    values: tuple[list[FieldType]] = tuple(
        get_trafo_field(field_name) for field_name in trafo_fields
    )

    print(trafo_fields)
    for row in range(len(values[0])):
        if selected_ids is None or row in selected_ids:
            print(tuple(values[col][row] for col in range(len(values))))
    print(trafo_fields)


def print_buses(
    selected_ids: Optional[tuple[int]] = None,
    bus_fields: tuple[str, ...] = (
        "number",
        "name",
        "base",
        "pu",
        "angleD",
        "nVLmHi",
        "nVLmLo",
    ),
):
    values: tuple[list[FieldType]] = tuple(
        get_bus_field(field_name) for field_name in bus_fields
    )

    print(bus_fields)
    for row in range(len(values[0])):
        if selected_ids is None or row in selected_ids:
            print(tuple(values[col][row] for col in range(len(values))))
    print(bus_fields)
