from typing import Callable, Final, Union

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


def print_branches(
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
    )
):
    values: tuple[list[FieldType]] = tuple(
        get_branch_field(field_name) for field_name in branch_fields
    )

    print(branch_fields)
    for row in range(len(values[0])):
        print(tuple(values[col][row] for col in range(len(values))))
    print(branch_fields)
