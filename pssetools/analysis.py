import enum

from pssetools import wrapped_funcs as wf
from pssetools.subsystem_data import (
    get_overloaded_branches_ids,
    get_overloaded_trafos_3w_ids,
    get_overloaded_trafos_ids,
    get_overvoltage_buses_ids,
    get_undervoltage_buses_ids,
    print_branches,
    print_buses,
    print_trafos,
    print_trafos_3w,
)


class Violations(enum.Flag):
    NO_VIOLATIONS = 0
    NOT_CONVERGED = enum.auto()
    BUS_OVERVOLTAGE = enum.auto()
    BUS_UNDERVOLTAGE = enum.auto()
    BRANCH_LOADING = enum.auto()
    TRAFO_LOADING = enum.auto()


def check_violations(
    max_bus_voltage_pu: float = 1.1,
    min_bus_voltage_pu: float = 0.9,
    max_branch_loading_pct: float = 100.0,
    max_trafo_loading_pct: float = 100.0,
    use_full_newton_raphson: bool = False,
) -> Violations:
    if not use_full_newton_raphson:
        wf.fdns()
    else:
        wf.fnsl()
    v: Violations = Violations.NO_VIOLATIONS
    if not wf.is_solved():
        v |= Violations.NOT_CONVERGED
        print("Case not solved!")
        return v
    print(f"\nCHECKING VIOLATIONS")
    if overvoltage_buses_ids := get_overvoltage_buses_ids(max_bus_voltage_pu):
        v |= Violations.BUS_OVERVOLTAGE
        print("Overloaded buses:")
        print_buses(overvoltage_buses_ids)
    if undervoltage_buses_ids := get_undervoltage_buses_ids(min_bus_voltage_pu):
        v |= Violations.BUS_UNDERVOLTAGE
        print("Overloaded buses:")
        print_buses(undervoltage_buses_ids)
    if overloaded_branches_ids := get_overloaded_branches_ids(max_branch_loading_pct):
        v |= Violations.BRANCH_LOADING
        print("Overloaded branches:")
        print_branches(overloaded_branches_ids)
    if overloaded_trafos_ids := get_overloaded_trafos_ids(max_trafo_loading_pct):
        v |= Violations.TRAFO_LOADING
        print("Overloaded 2-winding transformers:")
        print_trafos(overloaded_trafos_ids)
    if overloaded_trafos_3w_ids := get_overloaded_trafos_3w_ids(max_trafo_loading_pct):
        v |= Violations.TRAFO_LOADING
        print("Overloaded 3-winding transformers:")
        print_trafos_3w(overloaded_trafos_3w_ids)
    print(f"Detected violations: {v}\n")
    return v
