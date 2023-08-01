from pydantic import BaseSettings


class Envs(BaseSettings):
    pandapower_backend: bool = False
    treat_violations_as_warnings: bool = False
    verbose: bool = False

    class Config:
        env_prefix = "GRID_CAPACITY_"


envs = Envs()
