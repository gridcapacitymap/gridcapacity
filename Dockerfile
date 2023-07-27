FROM python:3

WORKDIR /usr/src/app
COPY . /usr/src/app
ENV GRID_CAPACITY_PANDAPOWER_BACKEND=1

RUN pip install pandapower numba pipenv
RUN pipenv install --skip-lock
