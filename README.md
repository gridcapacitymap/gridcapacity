# High level tools to work with PSS®E #

The PSS®E has a Python API to perform sample activities. This project provides the tools to automate the complex PSSE®E workflows.

## Running code #

Requirements:

- Python ≥ 3.8
- [pipenv](https://pipenv.readthedocs.io/en/latest/) ≥ 2018.11.15

```powershell
# Install project dependencies
pipenv install --skip-lock
# Run the simulation
pipenv run python -m pssetools [case_name.sav]
```

The `savnw.sav` will be used if the case name is omitted. The case name is a file name from the PSS®E `EXAMPLE` directory or an absolute file path.
