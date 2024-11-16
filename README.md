[![Pylint](https://github.com/m-erhardt/check-container-stats/actions/workflows/pylint.yml/badge.svg?branch=master)](https://github.com/m-erhardt/check-container-stats/actions/workflows/pylint.yml) [![pycodestyle](https://github.com/m-erhardt/check-container-stats/actions/workflows/pycodestyle.yml/badge.svg?branch=master)](https://github.com/m-erhardt/check-container-stats/actions/workflows/pycodestyle.yml) [![Unit tests](https://github.com/m-erhardt/check-container-stats/actions/workflows/python_unittests.yml/badge.svg?branch=master)](https://github.com/m-erhardt/check-container-stats/actions/workflows/python_unittests.yml) [![Release](https://img.shields.io/github/release/m-erhardt/check-container-stats.svg)](https://github.com/m-erhardt/check-container-stats/releases)
# check-container-stats

## About
- this repository contains a collection of Icinga / Nagios plugins to check Docker / PodMan containers
- Written for python3
- Only requires standard python modules, no additional dependencies
- To be executed i.e. via NRPE on the container host
  - Uses local Docker daemon socket file to query Docker
  - Uses `podman`-binary to query PodMan

## Documentation / plugins

- [check_container_stats_docker.py](docs/check_container_stats_docker.md) : check state & metrics of a single Docker container
- [check_docker_system.py](docs/check_docker_system.md) : check metrics of a Docker daemon
- [check_container_stats_podman.py](docs/check_container_stats_podman.md):  check state & metrics of a single PodMan container

## Contributing
- You're welcome to open issues or pull requests

