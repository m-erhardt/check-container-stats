#!/usr/bin/env python3
"""
###############################################################################
# check_container_stats_docker.py
# Icinga/Nagios plugin that checks the statistics of a Container via the Docker
# Daemon socket file
#
# Author        : Mauno Erhardt <mauno.erhardt@burkert.com>
# Copyright     : (c) 2021 Burkert Fluid Control Systems
# Source        : https://github.com/m-erhardt/check-container-stats
# License       : GPLv3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
###############################################################################
"""

import sys
import socket
import time
import json
from re import match
from argparse import ArgumentParser, Namespace as Arguments


def get_args() -> Arguments:
    """ Parse Arguments """
    parser = ArgumentParser(
        description="Icinga/Nagios plugin which checks health and statistics of a Container"
    )
    parser.add_argument("-c", "--container", required=True,
                        help="Name of the Container which should be checked",
                        type=str, dest='container_name')
    parser.add_argument("-t", "--timeout", required=False,
                        help="timeout in seconds", type=int, dest='timeout',
                        default=10)
    parser.add_argument("-s", "--socket", required=False,
                        help="Path to Docker socket file",
                        type=str, dest='socket',
                        default="/var/run/docker.sock")
    parser.add_argument('--wildcard', dest='wildcard', action='store_true',
                        help="--container is a wildcard, not an exact match")
    thresholds = parser.add_argument_group('Thresholds')
    thresholds.add_argument("--cpuwarn", required=False,
                            help="warning threshold for CPU usage (in %%)",
                            type=float, dest='cpuwarn')
    thresholds.add_argument("--cpucrit", required=False,
                            help="critical threshold for CPU usage (in %%)",
                            type=float, dest='cpucrit')
    thresholds.add_argument("--memwarn", required=False,
                            help="warning threshold for memory usage (in Bytes)",
                            type=int, dest='memwarn')
    thresholds.add_argument("--memcrit", required=False,
                            help="critical threshold for memory usage (in Bytes)",
                            type=int, dest='memcrit')
    thresholds.add_argument("--pidwarn", required=False,
                            help="warning threshold for number of processes in container",
                            type=int, dest='pidwarn')
    thresholds.add_argument("--pidcrit", required=False,
                            help="critical threshold for number of processes in container",
                            type=int, dest='pidcrit')

    args = parser.parse_args()

    # Remove unix:// from --socket - for backward compatibility
    if args.socket.startswith("unix://"):
        args.socket = args.socket[7:]

    return args


def exit_plugin(returncode, output, perfdata):
    """ Check status and exit accordingly """
    if returncode == 3:
        print("UNKNOWN - " + str(output))
        sys.exit(3)
    if returncode == 2:
        print("CRITICAL - " + str(output) + str(perfdata))
        sys.exit(2)
    if returncode == 1:
        print("WARNING - " + str(output) + str(perfdata))
        sys.exit(1)
    elif returncode == 0:
        print("OK - " + str(output) + str(perfdata))
        sys.exit(0)


def send_http_get(
    endpoint: str, socketfile: str = '/var/run/docker.sock',
    host: str = 'localhost', useragent: str = 'check_container_stats_docker.py'
) -> dict:
    """ Prepare HTTP post reqest to be sent to docker socket, evluate HTTP response """

    cmd: str = (f'GET { endpoint } HTTP/1.1\r\n'
                f'Host: { host }\r\n'
                f'User-Agent: { useragent }\r\n'
                f'Accept: application/json\r\n'
                f'Connection: close\r\n\r\n')

    # Split returned buffer into a list of lines
    buf_lines: list = send_socket_cmd(cmd, socketfile).splitlines()

    # Remove blank lines or lines containing only "0"
    buf_lines = [item for item in buf_lines if item not in ['', '0']]

    # Initialize return object
    response: dict = {
        'http_status': 0,
        'http_contenttype': '',
        'http_header_api-version': '',
        'http_response': {}
    }

    # Parse HTTP status and headers
    for line in buf_lines:
        if match(r"^HTTP/.\.. *", line):
            response["http_status"]: int = int(line.split(" ")[1])
        if match("^Content-Type: ", line):
            response["http_contenttype"]: str = line.split(":")[1].strip()
        if match("^Api-Version: ", line):
            response["http_header_api-version"]: str = line.split(":")[1].strip()

    # Parse HTTP resonse
    response["http_response"]: dict = json.loads(buf_lines[-1])

    if response["http_status"] != 200:
        exit_plugin(2, (f'Daemon API v{ response["http_header_api-version"] } returned HTTP '
                        f'{ response["http_status"] } while fetching { endpoint }: '
                        f'{ response["http_response"] }'), '')

    return response


def send_socket_cmd(cmd: str, socketfile: str) -> str:
    """ send cmd to docker socket and return reply as str """

    try:
        # Open connection to docker socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socketfile)
        sock.settimeout(3)

        # Send command
        sock.sendall(cmd.encode("ascii"))

        # Wait for server to come up with response
        time.sleep(0.01)

        # Create buffer for receiving
        buf = ""

        while True:
            # Write reply to buffer in chunks of 1024 bytes
            data = sock.recv(1024)

            if not data and len(buf) == 0:
                # No data received yet. Continue sleeping...
                time.sleep(0.01)

            elif not data:
                # Transfer already started but socket buffer currently empty...
                # Sometimes this while-loop reads information from the socket buffer faster than the
                # docker daemon can write to it - resulting in an incomplete response.
                # Thus we need to check if the buffer already contains a valid json object before leaving the loop
                if check_valid_response(buf):
                    break
            else:
                # Add data to buffer
                buf += data.decode()

        # Shut down sending
        sock.shutdown(socket.SHUT_WR)

        # Close socket connection
        sock.close()

    except FileNotFoundError:
        exit_plugin(3, f'Socket file { socketfile } not found!', "")
    except PermissionError:
        exit_plugin(3, f'Access to socket file { socketfile } denied!', "")
    except (TimeoutError, socket.timeout):
        exit_plugin(3, f'Connection to socket { socketfile } timed out!', "")
    except ConnectionError as err:
        exit_plugin(3, f'Error during socket connection: { err }', "")

    return buf


def check_valid_response(buffer: str) -> bool:
    """ Checks if the HTTP response is complete (contains a valid JSON object) """

    if len(buffer) == 0:
        # Buffer still empty
        return False

    http_lines: list = buffer.splitlines()

    # Find end of header lines
    start_pos: int = http_lines.index('')

    # Drop HTTP headers from lines
    del http_lines[0:start_pos]

    # Find line containing JSON response
    for line in http_lines:
        # Match JSON objects and arrays
        if match(r"\{", line) or match(r"\[", line):
            json_obj: str = line
            break

    if 'json_obj' not in locals():
        # No line with JSON object found
        return False

    try:
        # Validate JSON object
        json.loads(json_obj)
    except ValueError:
        # Invalid / incomplete response
        return False

    return True


def set_state(newstate: int, state: int) -> int:
    """ Set return state of plugin """

    if (newstate == 2) or (state == 2):
        returnstate = 2
    elif (newstate == 1) and (state not in [2]):
        returnstate = 1
    elif (newstate == 3) and (state not in [1, 2]):
        returnstate = 3
    else:
        returnstate = 0

    return returnstate


def convert_bytes_to_pretty(raw_bytes: int) -> str:
    """ converts raw bytes into human readable output """
    if raw_bytes >= 1099511627776:
        output = f'{ round(raw_bytes / 1024 **4, 2) }TiB'
    elif raw_bytes >= 1073741824:
        output = f'{ round(raw_bytes / 1024 **3, 2) }GiB'
    elif raw_bytes >= 1048576:
        output = f'{ round(raw_bytes / 1024 **2, 2) }MiB'
    elif raw_bytes >= 1024:
        output = f'{ round(raw_bytes / 1024, 2) }KiB'
    elif raw_bytes < 1024:
        output = f'{ raw_bytes }B'
    else:
        # Theoretically impossible, prevent pylint possibly-used-before-assignment
        raise ValueError('Impossible value in convert_bytes_to_pretty()')
    return output


def get_container_from_name(args: Arguments) -> dict:
    """ Query /containers/json filtering for name, return container JSON object as dict """

    # Query all containers that match the given name from /containers/json
    containers: dict = send_http_get(
        f'/v1.45/containers/json?all=true&filters={{"name":["{ args.container_name }"]}}',
        socketfile=args.socket
    )

    if len(containers["http_response"]) == 0:
        exit_plugin(2, f'No container matched name { args.container_name }', '')
    elif args.wildcard is True and len(containers["http_response"]) > 1:
        exit_plugin(2, f'Multiple containers matched wildcard name { args.container_name }', '')

    if args.wildcard is True:
        # We previously checked than wildcard name matched only one container - so this must be it
        container_info: dict = containers["http_response"][0]
    else:
        # loop over returned containers and check for match
        for cnt in containers["http_response"]:
            if f'/{ args.container_name }' in cnt["Names"]:
                container_info: dict = cnt
        if 'container_info' not in locals():
            exit_plugin(2, f'No container matched name { args.container_name }', '')

    return container_info


def calc_container_metrics(info: dict, stats: dict) -> dict:
    """ Extract, modify & derive values for container from raw API responses """
    # pylint: disable=too-many-branches

    container: dict = {}

    try:
        # Extract container name and id from api response
        container.update({"name": f'{ info["Names"][0][1:] }'})
        container.update({"id": f'{ info["Id"][:12] }'})
        container.update({"id_long": f'{ info["Id"] }'})

        # Get container state
        container.update({"state": f'{ info["State"] }'})
        container.update({"status": f'{ info["Status"] }'})

        # Get process statistics
        container.update({"pid_count": stats["pids_stats"].get("current", 0)})
        container.update({"pid_limit": stats["pids_stats"].get("limit", 0)})

        # Calculate CPU statistics
        # https://github.com/docker/cli/blob/master/cli/command/container/stats_helpers.go -> calculateCPUPercentUnix
        if container["state"] == "running":
            cpu_delta: float = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                               stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_cpu_delta: float = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
            if stats["cpu_stats"].get("online_cpus"):
                cpu_count: int = stats["cpu_stats"]["online_cpus"]
            else:
                cpu_count: int = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
            cpu_used_pct: float = (cpu_delta / system_cpu_delta) * cpu_count * 100.0
        else:
            cpu_used_pct: float = 0.0
        container.update({"cpu_pct": round(cpu_used_pct, 2)})

        # Calculate Memory statistics
        # https://github.com/docker/cli/blob/master/cli/command/container/stats_helpers.go
        # -> calculateMemUsageUnixNoCache
        used_memory: float = 0.0
        if container["state"] == "running":
            if stats["memory_stats"]["stats"].get("inactive_file") is not None:
                # Cgroups v2
                used_memory: float = stats["memory_stats"]["usage"] - stats["memory_stats"]["stats"]["inactive_file"]
            elif stats["memory_stats"]["stats"].get("total_inactive_file") is not None:
                # Cgroups v1
                used_memory: float = stats["memory_stats"]["usage"] - \
                    stats["memory_stats"]["stats"]["total_inactive_file"]
            else:
                exit_plugin(2, 'Docker API output did neither contain memory values for cgroupv1 nor cgroupv2', '')
        container.update({"memory": {"used": used_memory, "available": stats["memory_stats"].get("limit", 0)}})

        # Calculate network I/O statistics
        network_rx_bytes: int = 0
        network_tx_bytes: int = 0
        if container["state"] == "running":
            for network in stats["networks"].keys():
                network_rx_bytes += stats["networks"][network]["rx_bytes"]
                network_tx_bytes += stats["networks"][network]["tx_bytes"]
        container.update({"net_io": {"rx": network_rx_bytes, "tx": network_tx_bytes}})

        # Calculate filesystem/block device I/O statistics
        blkio_r: int = 0
        blkio_w: int = 0
        if container["state"] == "running" and stats["blkio_stats"]["io_service_bytes_recursive"] is not None:
            for item in stats["blkio_stats"]["io_service_bytes_recursive"]:
                if item["op"] == "read":
                    blkio_r += item["value"]
                elif item["op"] == "write":
                    blkio_w += item["value"]
        container.update({"blk_io": {"r": blkio_r, "w": blkio_w}})

    except KeyError as err:
        exit_plugin(2, f'Error while extracting values from JSON response: { err }', "")

    return container


def main():
    """ Main program code """

    # Get Arguments
    args = get_args()

    # Get daemon API version
    server_version: dict = send_http_get('/version', socketfile=args.socket)["http_response"]

    # Check of daemon is compatible with API v1.45
    if tuple(server_version["MinAPIVersion"].split('.')) > ("1", "45"):
        exit_plugin(2, (f'This plugin requires a docker daemon supporting API version 1.45 - '
                        f'Minimum supported version of this docker daemon is '
                        f'{ server_version["MinAPIVersion"] }'), '')

    # Get container id for name from /containers/json
    # Returns Container JSON object as dict
    container_info: dict = get_container_from_name(args)

    # Check if container is running, if not we can exit early without perfdata
    if container_info["State"] != "running":
        exit_plugin(2, f'Container { container_info["Names"][0][1:] } is { container_info["Status"] }', '')

    # Get container stats
    container_stats: dict = send_http_get(
            f'/v1.45/containers/{ container_info["Id"] }/stats?stream=false&one-shot=false',
            socketfile=args.socket
    )["http_response"]

    # Hand raw API responses over to calc_container_metrics to extract attributes and derive metrics
    container: dict = calc_container_metrics(container_info, container_stats)

    # Construct perfdata and output
    output = (f"{ container['name'] } ({ container['id'] }) is { container['status'] } - "
              f"CPU: { container['cpu_pct'] }%, "
              f"Memory: { convert_bytes_to_pretty(container['memory']['used']) }, "
              f"PIDs: {container['pid_count']}")

    perfdata = (f" | cpu={ container['cpu_pct'] }%;{ args.cpuwarn or '' };"
                f"{ args.cpucrit or '' };; "
                f"pids={ container['pid_count'] };{ args.pidwarn or '' };"
                f"{ args.pidcrit or '' };0;{ container['pid_limit'] } "
                f"mem={container['memory']['used']}B;{args.memwarn or ''};"
                f"{args.memcrit or ''};0;{ container['memory']['available'] } "
                f"net_send={ container['net_io']['tx'] }B;;;; "
                f"net_recv={ container['net_io']['rx'] }B;;;; "
                f"disk_read={ container['blk_io']['r'] }B;;;; "
                f"disk_write={ container['blk_io']['w'] }B;;;; ")

    # Set initial return code
    returncode = 0

    # Determine return code
    if "(unhealthy)" in container['status']:
        returncode = set_state(1, returncode)
    if container['state'] != "running":
        returncode = set_state(2, returncode)
    if args.cpuwarn is not None and args.cpuwarn < container['cpu_pct']:
        returncode = set_state(1, returncode)
    if args.cpucrit is not None and args.cpucrit < container['cpu_pct']:
        returncode = set_state(2, returncode)
    if args.memwarn is not None and args.memwarn < container['memory']['used']:
        returncode = set_state(1, returncode)
    if args.memcrit is not None and args.memcrit < container['memory']['used']:
        returncode = set_state(2, returncode)
    if args.pidwarn is not None and args.pidwarn < container['pid_count']:
        returncode = set_state(1, returncode)
    if args.pidcrit is not None and args.pidcrit < container['pid_count']:
        returncode = set_state(2, returncode)

    exit_plugin(returncode, output, perfdata)


if __name__ == "__main__":
    main()
