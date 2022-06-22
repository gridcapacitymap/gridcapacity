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
import os
import sys

if sys.platform == "win32" and not os.getenv("GRID_CAPACITY_PANDAPOWER_BACKEND"):
    print("Importing PSSE")
    from .psse import init_psse, wrapped_funcs

    init_psse()
else:
    print("Importing pandapower")
    from .pandapower import wrapped_funcs  # type: ignore[no-redef]

__all__ = ["wrapped_funcs"]
