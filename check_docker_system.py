#!/usr/bin/env python3
"""
###############################################################################
# check_docker_system.py
# Icinga/Nagios plugin that checks the statistics of Docker engine
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
import asyncio
from re import match
from argparse import ArgumentParser, Namespace as Arguments


def get_args() -> Arguments:
    """ Parse Arguments """
    parser = ArgumentParser(
        description="Icinga/Nagios plugin which checks a docker engine")

    parser.add_argument(
        "-s", "--socket", required=False, type=str, dest='socket', default="/var/run/docker.sock",
        help="Path to Docker socket (default: \"/var/run/docker.sock\")")

    parser.add_argument(
        '--debug', dest='debug', action='store_true', help="Print debug information", default=False
    )

    thresh = parser.add_argument_group('Thresholds')
    thresh.add_argument(
        "--minrunning", required=False, type=int, dest='minrunning', default=None,
        help="Exit WARNING if less than --minrunning containers are running")
    thresh.add_argument(
        "--maxpaused", required=False, type=int, dest='maxpaused', default=None,
        help="Exit WARNING if more than --maxpaused containers are paused")
    thresh.add_argument(
        "--maxstopped", required=False, type=int, dest='maxstopped', default=None,
        help="Exit WARNING if more than --maxstopped containers are stopped")
    thresh.add_argument(
        "--maximages", required=False, type=int, dest='maximages', default=None,
        help="Exit WARNING if more than --maximages are stored locally")
    thresh.add_argument(
        "--maxvolumes", required=False, type=int, dest='maxvolumes', default=None,
        help="Exit WARNING if more than --maxvolumes are stored locally")

    args = parser.parse_args()
    return args


def send_socket_cmd(cmd: str, socketfile: str) -> str:
    """ send cmd to docker socket and return reply as str """

    try:
        # Open connection to docker socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socketfile)
        sock.settimeout(1)

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
        if match(r"\{", line):
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


async def send_http_get(
        endpoint: str, socketfile: str = '/var/run/docker.sock',
        host: str = 'localhost', useragent: str = 'check_docker_system.py') -> dict:
    """ Prepare HTTP post reqest to be sent to docker socket """

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
        'http_response': ''
    }

    # Parse HTTP status and headers
    for line in buf_lines:
        if match(r"^HTTP/.\.. *", line):
            response["http_status"]: int = int(line.split(" ")[1])
        if match("^Content-Type: ", line):
            response["http_contenttype"]: str = line.split(":")[1].strip()

    # Parse HTTP resonse
    response["http_response"]: str = buf_lines[-1]

    return response


def parse_docker_sysinfo(docker_sysinfo: dict) -> dict:
    """ Parse values from Docker daemon JSON response """

    # Initialize dict
    engine_state: dict = {
        'containers': {
            'total': 0,
            'running': 0,
            'paused': 0,
            'stopped': 0
        },
        'images': 0,
        'cpus': 0,
        'memory': 0,
        'hostname': '',
        'server_version': ''
    }

    # Extract system info from JSON response
    try:
        engine_state["containers"]["total"] = int(docker_sysinfo["Containers"])
        engine_state["containers"]["running"] = int(docker_sysinfo["ContainersRunning"])
        engine_state["containers"]["paused"] = int(docker_sysinfo["ContainersPaused"])
        engine_state["containers"]["stopped"] = int(docker_sysinfo["ContainersStopped"])

        engine_state["images"] = int(docker_sysinfo["Images"])
        engine_state["cpus"] = int(docker_sysinfo["NCPU"])
        engine_state["memory"] = int(docker_sysinfo["MemTotal"])
        engine_state["hostname"] = docker_sysinfo["Name"]
        engine_state["server_version"] = docker_sysinfo["ServerVersion"]

    except (KeyError, TypeError) as err:
        exit_plugin(3, f'Error while extracting system information docker daemon response: {err}', '')

    return engine_state


def convert_bytes_to_pretty(raw_bytes: int):
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


def exit_plugin(returncode: int, output: str, perfdata: str):
    """ Check status and exit accordingly """
    if returncode == 3:
        print("UNKNOWN - " + str(output))
        sys.exit(3)
    if returncode == 2:
        print("CRITICAL - " + str(output) + " | " + str(perfdata))
        sys.exit(2)
    if returncode == 1:
        print("WARNING - " + str(output) + " | " + str(perfdata))
        sys.exit(1)
    elif returncode == 0:
        print("OK - " + str(output) + " | " + str(perfdata))
        sys.exit(0)


def main():
    """ Main program code """

    args: Arguments = get_args()

    # Get /info and /volumes from Docker socket
    loop = asyncio.get_event_loop()
    state, volumes = loop.run_until_complete(asyncio.gather(
        send_http_get('/info', socketfile=args.socket),
        send_http_get('/volumes', socketfile=args.socket),
    ))
    loop.close()

    # Check HTTP response code
    if state["http_status"] not in [200]:
        exit_plugin(3, f'Docker socket returned HTTP { state["http_status"] }: { state["http_response"] }', '')
    elif volumes["http_status"] not in [200]:
        exit_plugin(3, f'Docker socket returned HTTP { volumes["http_status"] }: { volumes["http_response"] }', '')

    if args.debug is True:
        print(json.dumps(state, indent=4))
        print(json.dumps(volumes, indent=4))

    # Try to parse JSON from docker daemon response
    try:
        docker_sysinfo: dict = json.loads(state["http_response"])
        docker_volinfo: dict = json.loads(volumes["http_response"])
    except json.decoder.JSONDecodeError as err:
        exit_plugin(3, f'Unable to parse valid JSON from docker daemon response: { err }', '')

    engine_state = parse_docker_sysinfo(docker_sysinfo)
    volcount: int = len(docker_volinfo["Volumes"])

    state = 0

    # Check thresholds
    if args.minrunning is not None and engine_state["containers"]["running"] < args.minrunning:
        state = set_state(1, state)
    if args.maxpaused is not None and engine_state["containers"]["paused"] > args.maxpaused:
        state = set_state(1, state)
    if args.maxstopped is not None and engine_state["containers"]["stopped"] > args.maxstopped:
        state = set_state(1, state)
    if args.maximages is not None and engine_state["images"] > args.maximages:
        state = set_state(1, state)
    if args.maxvolumes is not None and volcount > args.maxvolumes:
        state = set_state(1, state)

    output = (
        f'Containers: { engine_state["containers"]["total"] } '
        f'(Running: { engine_state["containers"]["running"] }, Paused: { engine_state["containers"]["paused"] }, '
        f'Stopped: { engine_state["containers"]["stopped"] }), Images: { engine_state["images"] }, '
        f'Volumes: { volcount }, '
        f'Docker version { engine_state["server_version"] } running with '
        f'{ engine_state["cpus"] } CPUs and { convert_bytes_to_pretty(engine_state["memory"]) } memory'
    )
    perfdata = (
        f'\'containers_running\'={ engine_state["containers"]["running"] };;;0;'
        f'{ engine_state["containers"]["total"] } '
        f'\'containers_paused\'={ engine_state["containers"]["paused"] };{ args.maxpaused or "" };;0;'
        f'{ engine_state["containers"]["total"] } '
        f'\'containers_stopped\'={ engine_state["containers"]["stopped"] };{ args.maxstopped or "" };;0;'
        f'{ engine_state["containers"]["total"] } '
        f'\'images\'={ engine_state["images"] };{ args.maximages or "" };;0; '
        f'\'volumes\'={ volcount };{ args.maxvolumes or "" };;0;'
    )

    exit_plugin(state, output, perfdata)


if __name__ == "__main__":
    main()
