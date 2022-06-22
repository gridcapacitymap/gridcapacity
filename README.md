# High level tools to work with PSS®E #

The PSS®E has a Python API to perform sample activities. This project provides the tools to automate the complex PSSE®E
workflows. They include

- wrappers for sample subsystems APIs
- routines for analysis of:
  - violations
  - contingencies
  - headroom capacity
- JSON writer for headroom and violations statistics

## Running code #

Requirements:

- Python 3.9
- [pipenv](https://pipenv.readthedocs.io/en/latest/) ≥ 2018.11.15

```powershell
# Install project dependencies
pipenv install --skip-lock
# Run the simulation
pipenv run python -m pssetools sample_config.json
```

The config file name, `sample_config.json` in this example, is the required argument. Its path should be an absolute
path or a path relative to this repository root. The config file is described in the next section.

The headroom analysis is performed. The output files for headroom and violations statistics are written in JSON format.
They are written to the same directory as a case file if the case file name is an absolute path or to the project root
directory if the case file name is a relative path.

## Configuration file #

All the configuration options are described as a `ConfigModel` class found in the [config.py](gridcapacity/config.py)
file.

There are 3 required options:

```json
{
    "case_name": "savnw.sav",
    "upper_load_limit_p_mw": 100.0,
    "upper_gen_limit_p_mw": 80.0
}
```

The `case_name` is a file name from the PSS®E `EXAMPLE` directory or an absolute file path.

## Environment variables #

There are debugging features that could be enabled using the environment variables.

| ENV                                          | Description                 |
|----------------------------------------------|:----------------------------|
| `GRID_CAPACITY_PANDAPOWER_BACKEND`           | Force PandaPower on Windows |
| `GRID_CAPACITY_TREAT_VIOLATIONS_AS_WARNINGS` | Enable violations output    |
| `GRID_CAPACITY_VERBOSE`                      | Enable verbose output       |

To start the project with verbose output enabled, run:

```powershell
$env:GRID_CAPACITY_VERBOSE = ’1’
pipenv run python -m pssetools sample_config.json
```

## Running tests #

```powershell
pipenv run python -m unittest
```

## Developer tools #

To install developer tools, run:

```powershell
pipenv install --skip-lock --dev
```

Format code and check typing errors with

```powershell
pipenv run isort . ; black . ; mypy .
```

Check unused imports with

```powershell
pipenv run autoflake --remove-all-unused-imports -r .
```
