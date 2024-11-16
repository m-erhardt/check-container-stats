# check_container_stats_docker.py

check state & metrics of a single Docker container via the Unix socket file of the Docker daemon.

## Usage example
```
./check_container_stats_docker.py -c example-container -s /run/user/1000/docker.sock
OK - example-container (2c56d4f8816b) is Up 2 days - CPU: 0.0%, Memory: 65.8MiB, PIDs: 5 | cpu=0.0%;;;; pids=5;;;0;17534 mem=69001216B;;;0;524288000 net_send=17173926B;;;; net_recv=863452B;;;; disk_read=409600B;;;; disk_write=119078912B;;;;
```

## Usage
```
usage: check_container_stats_docker.py [-h] -c CONTAINER_NAME [-t TIMEOUT] [-s SOCKET] [--wildcard] [--cpuwarn CPUWARN] [--cpucrit CPUCRIT] [--memwarn MEMWARN] [--memcrit MEMCRIT] [--pidwarn PIDWARN] [--pidcrit PIDCRIT]

Icinga/Nagios plugin which checks health and statistics of a Container

optional arguments:
  -h, --help            show this help message and exit
  -c CONTAINER_NAME, --container CONTAINER_NAME
                        Name of the Container which should be checked
  -t TIMEOUT, --timeout TIMEOUT
                        timeout in seconds
  -s SOCKET, --socket SOCKET
                        Path to Docker socket file
  --wildcard            --container is a wildcard, not an exact match

Thresholds:
  --cpuwarn CPUWARN     warning threshold for CPU usage (in %)
  --cpucrit CPUCRIT     critical threshold for CPU usage (in %)
  --memwarn MEMWARN     warning threshold for memory usage (in Bytes)
  --memcrit MEMCRIT     critical threshold for memory usage (in Bytes)
  --pidwarn PIDWARN     warning threshold for number of processes in container
  --pidcrit PIDCRIT     critical threshold for number of processes in container
```

![Output of check_container_stats_docker.py](img/check_container_stats_docker.png?raw=true "Output of check_container_stats_docker.py")
