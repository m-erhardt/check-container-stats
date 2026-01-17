#!/usr/bin/env python3

import sys
import unittest
import unittest.mock

sys.path.append('..')
sys.path.append('.')

import check_container_stats_docker
import check_container_stats_podman
import check_docker_system

class TestScriptExecution(unittest.TestCase):
    """
    Test if main() function of non-async plugins executes without exception and performs clean exit
    """

    def test_check_container_stats_docker_help(self):
        with unittest.mock.patch('sys.argv', ['check_container_stats_docker.py', '--help']):
            with self.assertRaises(SystemExit) as exit_code:
                check_container_stats_docker.main()

            # Test if exit code was 0
            self.assertEqual(exit_code.exception.code, 0)

    def test_check_container_stats_podman_help(self):
        with unittest.mock.patch('sys.argv', ['check_container_stats_podman.py', '--help']):
            with self.assertRaises(SystemExit) as exit_code:
                check_container_stats_podman.main()

            # Test if exit code was 0
            self.assertEqual(exit_code.exception.code, 0)


class TestAsyncScriptExecution(unittest.IsolatedAsyncioTestCase):
    """
    Test if main() function of async plugins executes without exception and performs clean exit
    """

    async def test_check_docker_system_help(self):
        with unittest.mock.patch('sys.argv', ['check_docker_system.py', '--help']):
            with self.assertRaises(SystemExit) as exit_code:
                await check_docker_system.main()

            # Test if exit code was 0
            self.assertEqual(exit_code.exception.code, 0)


class TestMetricDetection(unittest.TestCase):

    def test_podman_metric_unit_detection(self):
        # Check check_container_stats_podman.py for different metric notations
        self.assertEqual(check_container_stats_podman.convert_to_bytes('105 MB'), 105000000)
        self.assertEqual(check_container_stats_podman.convert_to_bytes('105TiB'), 115448720916480)
        self.assertEqual(check_container_stats_podman.convert_to_bytes('512 B'), 512)
        self.assertEqual(check_container_stats_podman.convert_to_bytes('105e+3MB'), 105000000000)
        self.assertEqual(check_container_stats_podman.convert_to_bytes('--'), 0)


if __name__ == '__main__':
    unittest.main()
