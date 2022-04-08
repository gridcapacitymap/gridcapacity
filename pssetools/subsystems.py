from dataclasses import dataclass

from pssetools.subsystem_data import FieldType, get_load_field


@dataclass
class Load:
    number: int
    ex_name: str
    load_id: str
    mva_act: complex


class Loads:
    def __init__(self) -> None:
        load_fields: tuple[str, ...] = (
            "number",
            "exName",
            "id",
            "mvaAct",
        )
        self._raw_loads: tuple[list[FieldType], ...] = tuple(
            get_load_field(field_name) for field_name in load_fields
        )

    def __iter__(self) -> Load:
        for load_idx in range(len(self._raw_loads[0])):
            yield Load(
                *(
                    self._raw_loads[field][load_idx]
                    for field in range(len(self._raw_loads))
                )
            )
