#!/usr/bin/env python3
"""
###############################################################################
# check_container_stats_docker.py
# Icinga/Nagios plugin that checks the statistics of a Container via the
# "docker ps/stats" command
#
#
# Author        : Mauno Erhardt <mauno.erhardt@burkert.com>
# Copyright     : (c) 2021 Burkert Fluid Control Systems
# Source        : https://github.com/m-erhardt/check-container-stats
# License       : GPLv3 (http://www.gnu.org/licenses/gpl-3.0.txt)
#
###############################################################################
"""

import sys
import subprocess
from re import findall, match
from string import ascii_letters
from argparse import ArgumentParser


def get_args():
    """ Parse Arguments """
    parser = ArgumentParser(
                 description="Icinga/Nagios plugin which checks health and statistics of a \
                              Container")
    parser.add_argument("-c", "--container", required=True,
                        help="Name of the Container which should be checked",
                        type=str, dest='container_name')
    parser.add_argument("-t", "--timeout", required=False,
                        help="timeout in seconds", type=int, dest='timeout',
                        default=10)
    parser.add_argument("-s", "--socket", required=False,
                        help="Path to Docker socket, sets environment variable \
                              DOCKER_HOST",
                        type=str, dest='socket',
                        default="unix:///var/run/docker.sock")
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


def get_container_name(args, docker_env):
    """ wildcard container name, get exact container name"""

    result = subprocess.run(['docker', 'ps', '-a', '-f', f'name={args.container_name}',
                             '--format', '"{{.Names}}"'],
                            shell=False,
                            check=False,
                            env=docker_env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    # Check if command exited without error code
    if result.returncode != 0:
        exit_plugin(3, f'docker stats command returned error: {result.stderr}', '')

    # Check if the command returned any putput
    elif len(result.stdout.decode()) == 0:
        exit_plugin(2, f'Container {args.container_name} not found', '')

    return str(result.stdout.decode().split("\n")[0].strip("\""))


def get_container_pslist(args, docker_env):
    """ execute docker ps"""

    # Execute "docker ps" command
    result = subprocess.run(['docker', 'ps', '-a', '-f', f'name=^/{args.container_name}$',
                             '--format', '"{{.Names}},{{.Status}},{{.Size}},{{.RunningFor}}"'],
                            shell=False,
                            check=False,
                            env=docker_env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    # Check if command exited without error code
    if result.returncode != 0:
        exit_plugin(3, f'docker stats command returned error: {result.stderr}', '')

    # Check if the command returned any putput
    elif len(result.stdout.decode()) == 0:
        exit_plugin(2, f'Container {args.container_name} not found', '')

    # Initialize return object
    container_ps = {'name': '', 'state': '', 'size': '', 'running_for': ''}

    # Extract first line from output
    output = result.stdout.decode().split("\n")[0].strip("\"")

    container_ps['name'] = output.split(",")[0]
    container_ps['state'] = output.split(",")[1]
    container_ps['size'] = output.split(",")[2]
    container_ps['running_for'] = output.split(",")[3]

    # Check if container is up
    if not match("^Up *", container_ps['state']):
        exit_plugin(2, f"Container {args.container_name} is {container_ps['state']}", '')

    return container_ps


def get_container_stats(args, docker_env):
    """ execute docker stat"""

    # Execute "docker stats" command
    result = subprocess.run(['docker', 'stats', args.container_name, '--no-stream', '--format',
                             '"{{.Name}},{{.ID}},{{.CPUPerc}},{{.MemUsage}},\
                               {{.NetIO}},{{.BlockIO}},{{.PIDs}}"'],
                            shell=False,
                            check=False,
                            env=docker_env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    # Check if command exited without error code
    if result.returncode != 0:
        exit_plugin(3, f'docker stats command returned error: {result.stderr}', '')

    # Check if the command returned any putput
    elif len(result.stdout.decode()) == 0:
        exit_plugin(2, (f'docker stats did not return any output for '
                        f'Container {args.container_name}'), '')

    # Initialize return object
    container_stats = {'name': '', 'id': '', 'cpu_perc': 0.0,
                       'mem_used': '', 'mem_used_byte': 0, 'mem_total': '', 'mem_total_byte': 0,
                       'net_send': '', 'net_send_byte': 0, 'net_recv': '', 'net_recv_byte': 0,
                       'block_read': 0, 'block_write': 0,
                       'pids': 0}

    # Extract first line from output
    output = result.stdout.decode().split("\n")[0].strip("\"")

    container_stats['name'] = output.split(",")[0]
    container_stats['id'] = output.split(",")[1][0:12]
    container_stats['cpu_perc'] = float(output.split(",")[2].rstrip('%'))
    container_stats['mem_used'] = output.split(",")[3].split("/")[0].strip()
    container_stats['mem_used_byte'] = convert_to_bytes(output.split(",")[3].split("/")[0].strip())
    container_stats['mem_total'] = output.split(",")[3].split("/")[1].strip()
    container_stats['mem_total_byte'] = convert_to_bytes(output.split(",")[3].split("/")[1].strip())
    container_stats['net_send'] = output.split(",")[4].split("/")[0].strip()
    container_stats['net_send_byte'] = convert_to_bytes(output.split(",")[4].split("/")[0].strip())
    container_stats['net_recv'] = output.split(",")[4].split("/")[1].strip()
    container_stats['net_recv_byte'] = convert_to_bytes(output.split(",")[4].split("/")[1].strip())
    container_stats['block_read'] = output.split(",")[5].split("/")[0].strip()
    container_stats['block_read_byte'] = convert_to_bytes(output.split(",")[5].
                                                          split("/")[0].strip())
    container_stats['block_write'] = output.split(",")[5].split("/")[1].strip()
    container_stats['block_write_byte'] = convert_to_bytes(output.split(",")[5].
                                                           split("/")[1].strip())
    container_stats['pids'] = int(output.split(",")[6])

    return container_stats


def convert_to_bytes(inputstr):
    """ converts docker output units to raw bytes """

    value = float(inputstr.replace(" ", "").rstrip(ascii_letters))
    unit = findall(r"\d[a-zA-Z]+$", inputstr.replace(" ", ""))[0].lstrip('01234565789')

    if unit == 'TB':
        value = round(value * 1000000000000)
    elif unit == 'GB':
        value = round(value * 1000000000)
    elif unit == 'MB':
        value = round(value * 1000000)
    elif unit in ['KB', 'kB']:
        value = round(value * 1000)
    elif unit == 'B':
        value = round(value)
    elif unit == 'TiB':
        value = round(value * 1099511627776)
    elif unit == 'GiB':
        value = round(value * 1073741824)
    elif unit == 'MiB':
        value = round(value * 1048576)
    elif unit == 'KiB':
        value = round(value * 1024)
    else:
        exit_plugin(3, f'Unknown metric unit in "docker stats" output: {unit}', "")

    return int(value)


def main():
    """ Main program code """

    # Get Arguments
    args = get_args()

    # environment variables for "docker" command
    docker_env = {}
    docker_env["DOCKER_HOST"] = args.socket

    # parameter --container is not an exact match but an wildcard, get container name
    if args.wildcard is True:
        args.container_name = get_container_name(args, docker_env)

    # Execute "docker ps" and "docker stats"
    container_ps = get_container_pslist(args, docker_env)
    container_stats = get_container_stats(args, docker_env)

    # Construct perfdata and output
    output = (f"{container_stats['name']} ({container_stats['id']}) is {container_ps['state']} - "
              f"CPU: {container_stats['cpu_perc']}%, Memory: {container_stats['mem_used']}, "
              f"PIDs: {container_stats['pids']}")

    perfdata = (f" | cpu={container_stats['cpu_perc']}%;{args.cpuwarn or ''};"
                f"{args.cpucrit or ''};; "
                f"pids={container_stats['pids']};{args.pidwarn or ''};{args.pidcrit or ''};; "
                f"mem={container_stats['mem_used_byte']}B;{args.memwarn or ''};"
                f"{args.memcrit or ''};;"
                f"{container_stats['mem_total_byte']} "
                f"net_send={container_stats['net_send_byte']}B;;;; "
                f"net_recv={container_stats['net_recv_byte']}B;;;; "
                f"disk_read={container_stats['block_read_byte']}B;;;; "
                f"disk_write={container_stats['block_write_byte']}B;;;; ")

    # determine return code
    returncode = 0

    if "(unhealthy)" in container_ps['state']:
        returncode = 1
    if args.cpucrit is not None and args.cpucrit < container_stats['cpu_perc']:
        returncode = 2
    if args.cpuwarn is not None and args.cpuwarn < container_stats['cpu_perc'] and returncode != 2:
        returncode = 1
    if args.memcrit is not None and args.memcrit < container_stats['mem_used_byte']:
        returncode = 2
    if args.memwarn is not None and args.memwarn < container_stats['mem_used_byte'] \
       and returncode != 2:
        returncode = 1
    if args.pidcrit is not None and args.pidcrit < container_stats['pids']:
        returncode = 2
    if args.pidwarn is not None and args.pidwarn < container_stats['pids'] and returncode != 2:
        returncode = 1

    exit_plugin(returncode, output, perfdata)


if __name__ == "__main__":
    main()
