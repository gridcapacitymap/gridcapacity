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
import errno
import os
import sys
import winreg
from pathlib import Path
from typing import Final, Optional

assert sys.platform == "win32"


def get_psse35_paths() -> list[str]:
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\PTI\PSSE 35") as pti_key:
        last_sub_key: Optional[str] = None
        try:
            for sub_key_idx in range(10):
                last_sub_key = winreg.EnumKey(pti_key, sub_key_idx)
        except OSError:
            pass
        if last_sub_key is None:
            raise (RuntimeError("PSSE 35 keys not found in Windows Registry"))
        with winreg.OpenKey(pti_key, rf"{last_sub_key}\Product Paths") as paths_key:
            try:
                psse_paths: list[str] = list(
                    winreg.QueryValueEx(paths_key, key)[0]
                    for key in (
                        "PsseExePath",
                        f"PsseLocalPsspy{sys.version_info[0]}{sys.version_info[1]}Path",
                    )
                )
            except FileNotFoundError as e:
                psse_minor_version: Final[str] = last_sub_key
                raise RuntimeError(
                    f"Python {sys.version_info[0]}{sys.version_info[1]} "
                    f"is not supported by PSSE 35.{psse_minor_version}"
                ) from e
            for path in psse_paths:
                if not Path(path).exists:
                    raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), str(path))
            return psse_paths
