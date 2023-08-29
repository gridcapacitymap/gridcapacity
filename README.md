# Grid capacity #

The power flows simulation for grid capacity analysis is performed using either
- [Siemens PSS®E](https://new.siemens.com/global/en/products/energy/energy-automation-and-smart-grid/pss-software/pss-e.html) or
- [pandapower](https://www.pandapower.org/)
as a backend.

The code includes:
- JSON configuration file parser
- routines for analysis of:
  - violations
  - contingencies
  - grid capacity
- backend wrappers to load model and work with subsystems
- JSON writer for analysis results and statistics

## Running code #

Requirements:

- Python 3.9
- [pipenv](https://pipenv.readthedocs.io/en/latest/)

```powershell
# Install project dependencies
pipenv install --skip-lock
# Run the simulation
pipenv run python -m gridcapacity sample_config.json
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

The `case_name` should be an absolute file path. If the path is relative, its processing depends on the backend:
- for the PSS®E backend, it is relative to PSS®E `EXAMPLE` directory
- for the `pandapower` backend, it is relative to this repository root

## Environment variables #

PandaPower backend usage and debugging features could be enabled using the environment variables.

| ENV                                          | Description                 |
|----------------------------------------------|:----------------------------|
| `GRID_CAPACITY_PANDAPOWER_BACKEND`           | Force PandaPower on Windows |
| `GRID_CAPACITY_TREAT_VIOLATIONS_AS_WARNINGS` | Enable violations output    |
| `GRID_CAPACITY_VERBOSE`                      | Enable verbose output       |

To start the project with verbose output enabled, run:

```powershell
$env:GRID_CAPACITY_VERBOSE = ’1’
pipenv run python -m gridcapacity sample_config.json
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
pipenv run isort . ; black . ; mypy .; prospector
```

Check unused imports with

```powershell
pipenv run autoflake --remove-all-unused-imports -r .
```

## Headless execution

Possilbe with `pandapower` on linux. Example with included test case follows

```
# build docker image (once)
docker build -t gridcapacity/pandapower .

# create example config
cat << EOF > ./test_config.json
{
    "case_name": "sample_data/savnw.json",
    "upper_load_limit_p_mw": 200.0,
    "upper_gen_limit_p_mw": 200.0,
    "selected_buses_ids":  [3008, 3005, 3011],
    "connection_scenario": {},
    "contingency_scenario": {
        "branches": [],
        "trafos": []
    }
}
EOF

# run calculation
docker run -it --rm --name gridcapacity -w /usr/src/app -v "$PWD":/usr/src/app:Z gridcapacity/pandapower pipenv run python -m gridcapacity test_config.json
```
