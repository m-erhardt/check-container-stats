# check_docker_system.py
plugin that checks metrics of a docker daemon via the Unix socket file.

## Usage example
```
./check_docker_system.py -s /run/user/1000/docker.sock
OK - Containers: 6 (Running: 1, Paused: 0, Stopped: 5), Images: 14, Volumes: 5, Docker version 27.3.1 running with 2 CPUs and 2.71GiB memory | 'containers_running'=1;;;0;6 'containers_paused'=0;;;0;6 'containers_stopped'=5;;;0;6 'images'=14;;;0; 'volumes'=5;;;0;
```

## Usage
```
usage: check_docker_system.py [-h] [-s SOCKET] [--debug] [--minrunning MINRUNNING] [--maxpaused MAXPAUSED] [--maxstopped MAXSTOPPED] [--maximages MAXIMAGES] [--maxvolumes MAXVOLUMES]

Icinga/Nagios plugin which checks a docker engine

optional arguments:
  -h, --help            show this help message and exit
  -s SOCKET, --socket SOCKET
                        Path to Docker socket (default: "/var/run/docker.sock")
  --debug               Print debug information

Thresholds:
  --minrunning MINRUNNING
                        Exit WARNING if less than --minrunning containers are running
  --maxpaused MAXPAUSED
                        Exit WARNING if more than --maxpaused containers are paused
  --maxstopped MAXSTOPPED
                        Exit WARNING if more than --maxstopped containers are stopped
  --maximages MAXIMAGES
                        Exit WARNING if more than --maximages are stored locally
  --maxvolumes MAXVOLUMES
                        Exit WARNING if more than --maxvolumes are stored locally
```

![Output of check_docker_system.py](img/check_docker_system.png?raw=true "Output of check_docker_system.py")
