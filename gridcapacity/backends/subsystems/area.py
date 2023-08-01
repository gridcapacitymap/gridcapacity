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
import logging
import sys

from ...envs import envs

if sys.platform == "win32" and not envs.pandapower_backend:
    import psspy

    from ..psse import wrapped_funcs as wf

log = logging.getLogger(__name__)


class AreaByNumber(dict[int, str]):
    def __init__(self) -> None:
        super().__init__()
        names = wf.aareachar(string="areaname")[0]
        numbers = wf.aareaint(string="number")[0]
        for name, number in zip(names, numbers):
            self[number] = name
