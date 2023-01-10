[![Pylint](https://github.com/m-erhardt/check-container-stats/actions/workflows/pylint.yml/badge.svg?branch=master)](https://github.com/m-erhardt/check-container-stats/actions/workflows/pylint.yml) [![pycodestyle](https://github.com/m-erhardt/check-container-stats/actions/workflows/pycodestyle.yml/badge.svg?branch=master)](https://github.com/m-erhardt/check-container-stats/actions/workflows/pycodestyle.yml) [![Unit tests](https://github.com/m-erhardt/check-container-stats/actions/workflows/python_unittests.yml/badge.svg?branch=master)](https://github.com/m-erhardt/check-container-stats/actions/workflows/python_unittests.yml) [![Release](https://img.shields.io/github/release/m-erhardt/check-container-stats.svg)](https://github.com/m-erhardt/check-container-stats/releases)
# check-container-stats

## About
* this repository contains a collection of Icinga / Nagios plugins to check Docker / PodMan containers
* Written for python3
* Only requires standard python modules, no additional dependencies
* To be executed i.e. via NRPE on the container host, uses the local "docker"/"podman" binary to query container metrics

## Documentation

### Usage example

```bash
# default usage
./check_container_stats_docker.py -c containername
OK - containername (b343972b5de9) is Up 3 days - CPU: 8.65%, Memory: 10.62 GiB, PIDs: 304 | cpu=8.65%;;;; pids=304;;;; mem=11403138171B;;;;33565169418 net_send=2570000000B;;;; net_recv=2750000000B;;;; disk_read=1580000000B;;;; disk_write=3760000000B;;;;

# With custom socket file location (i.e. for rootless docker or multiple instances of docker daemon on one host)
./check_container_stats_docker.py -c containername --socket 'unix:///run/user/1000/docker.sock'

# Search for a container that matches *<containername>* (default is to only search for exact matches)
./check_container_stats_docker.py -c containername --wildcard
```

### Usage
```
usage: check_container_stats_docker.py [-h] -c CONTAINER_NAME [-t TIMEOUT]
                                       [-s SOCKET] [--wildcard]
                                       [--cpuwarn CPUWARN] [--cpucrit CPUCRIT]
                                       [--memwarn MEMWARN] [--memcrit MEMCRIT]
                                       [--pidwarn PIDWARN] [--pidcrit PIDCRIT]

Icinga/Nagios plugin which checks health and statistics of a Container

optional arguments:
  -h, --help            show this help message and exit
  -c CONTAINER_NAME, --container CONTAINER_NAME
                        Name of the Container which should be checked
  -t TIMEOUT, --timeout TIMEOUT
                        timeout in seconds
  -s SOCKET, --socket SOCKET
                        Path to Docker socket, sets environment variable
                        DOCKER_HOST
  --wildcard            --container is a wildcard, not an exact match

Thresholds:
  --cpuwarn CPUWARN     warning threshold for CPU usage (in %)
  --cpucrit CPUCRIT     critical threshold for CPU usage (in %)
  --memwarn MEMWARN     warning threshold for memory usage (in Bytes)
  --memcrit MEMCRIT     critical threshold for memory usage (in Bytes)
  --pidwarn PIDWARN     warning threshold for number of processes in container
  --pidcrit PIDCRIT     critical threshold for number of processes in
                        container
```

![Icinga2 service check](img/check_container_stats_1.png?raw=true "Icinga2 service check")
![Icinga2 service check](img/check_container_stats_2.png?raw=true "Icinga2 service check")


## Contributing
* You're welcome to open issues or pull requests

