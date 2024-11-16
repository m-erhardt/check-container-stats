# check_container_stats_podman.py

check state & metrics of a single PodMan container by calling `podman ps` & `podman stats`.

## Usage example
```
./check_container_stats_podman.py -c example-container
OK - example-container (511b92dd29fc) is Up 4 days (healthy) - CPU: 0.07%, Memory: 43.75MB, PIDs: 13 | cpu=0.07%;;;; pids=13;;;; mem=43750000B;;;;3836000000 net_send=52230000B;;;; net_recv=31160000B;;;; disk_read=188400B;;;; disk_write=76290000B;;;;
```
## Usage
```
usage: check_container_stats_podman.py [-h] -c CONTAINER_NAME [-t TIMEOUT] [--cpuwarn CPUWARN] [--cpucrit CPUCRIT] [--memwarn MEMWARN] [--memcrit MEMCRIT] [--pidwarn PIDWARN] [--pidcrit PIDCRIT]

Icinga/Nagios plugin which checks health and statistics of a Container

optional arguments:
  -h, --help            show this help message and exit
  -c CONTAINER_NAME, --container CONTAINER_NAME
                        Name of the Container which should be checked
  -t TIMEOUT, --timeout TIMEOUT
                        timeout in seconds

Thresholds:
  --cpuwarn CPUWARN     warning threshold for CPU usage (in %)
  --cpucrit CPUCRIT     critical threshold for CPU usage (in %)
  --memwarn MEMWARN     warning threshold for memory usage (in Bytes)
  --memcrit MEMCRIT     critical threshold for memory usage (in Bytes)
  --pidwarn PIDWARN     warning threshold for number of processes in container
  --pidcrit PIDCRIT     critical threshold for number of processes in container
```

![Output of check_container_stats_podman.py](img/check_container_stats_podman.png?raw=true "Output of check_container_stats_podman.py")

