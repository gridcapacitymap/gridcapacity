FROM python:3.9

WORKDIR /usr/src/app
COPY . /usr/src/app

ENV PYTHONPATH=/usr/src/app
ENV GRID_CAPACITY_PANDAPOWER_BACKEND=1

RUN pip install pipenv
RUN pipenv install --skip-lock numba==0.56.4 pandapower[all]~=2.13.1
RUN pipenv install --skip-lock
