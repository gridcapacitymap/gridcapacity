"""
Copyright 2023 Vattenfall AB

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
from typing import Union

from .branch import Branch, Branches, DataExportBranch, DataExportBranches
from .bus import (
    Bus,
    Buses,
    DataExportBus,
    DataExportBuses,
    TemporaryBusLoad,
    TemporaryBusMachine,
)
from .gen import DataExportMachine, DataExportMachines, Machine, Machines
from .load import DataExportLoad, DataExportLoads, Load, Loads
from .swing_bus import SwingBuses
from .trafo import DataExportTrafo, DataExportTrafos, Trafo, Trafos
from .trafo3w import DataExportTrafo3w, DataExportTrafos3w, Trafo3w, Trafos3w
from .utils import Printable

TemporaryBusSubsystem = Union[TemporaryBusLoad, TemporaryBusMachine]

Subsystems = Union[Buses, Branches, SwingBuses, Trafos, Trafos3w]
