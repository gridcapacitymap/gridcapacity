import errno
import os
import sys
import winreg
from pathlib import Path
from typing import Final, List, Optional


def get_psse35_paths() -> List[str]:
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
                psse_paths: List[str] = list(
                    winreg.QueryValueEx(paths_key, key)[0]
                    for key in (
                        "PsseExePath",
                        f"PsseLocalPsspy{'{}{}'.format(*sys.version_info[:2])}Path",
                    )
                )
            except FileNotFoundError:
                psse_minor_version: Final[str] = last_sub_key
                raise RuntimeError(
                    f"Python {'{}.{}'.format(*sys.version_info[:2])} "
                    f"is not supported by PSSE 35.{psse_minor_version}"
                )
            for path in psse_paths:
                if not Path(path).exists:
                    raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), str(path))
            return psse_paths
