import enum

from pssetools import wrapped_funcs as wf
from pssetools.subsystem_data import (
    get_overloaded_branches_ids,
    get_overvoltage_buses_ids,
    get_undervoltage_buses_ids,
    print_branches,
    print_buses,
)


class Violations(enum.Flag):
    NO_VIOLATIONS = 0
    NOT_CONVERGED = enum.auto()
    BUS_OVERVOLTAGE = enum.auto()
    BUS_UNDERVOLTAGE = enum.auto()
    BRANCH_LOADING = enum.auto()


def check_violations(
    max_pu_bus_voltage: float = 1.1,
    min_pu_bus_voltage: float = 0.9,
    max_pct_branch_loading: float = 100.0,
) -> Violations:
    wf.fdns()
    v: Violations = Violations.NO_VIOLATIONS
    if not wf.is_solved():
        v |= Violations.NOT_CONVERGED
        print("Case not solved!")
        return v
    print(f"\nCHECKING VIOLATIONS")
    if overloaded_branches_ids := get_overloaded_branches_ids(max_pct_branch_loading):
        v |= Violations.BRANCH_LOADING
        print("Overloaded branches:")
        print_branches(overloaded_branches_ids)
    if overvoltage_buses_ids := get_overvoltage_buses_ids(max_pu_bus_voltage):
        v |= Violations.BUS_OVERVOLTAGE
        print("Overloaded buses:")
        print_buses(overvoltage_buses_ids)
    if undervoltage_buses_ids := get_undervoltage_buses_ids(min_pu_bus_voltage):
        v |= Violations.BUS_UNDERVOLTAGE
        print("Overloaded buses:")
        print_buses(undervoltage_buses_ids)
    print(f"Detected violations: {v}\n")
    return v
