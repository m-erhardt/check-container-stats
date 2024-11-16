#!/usr/bin/env python3

import sys
import unittest

sys.path.append('..')
sys.path.append('.')

import check_container_stats_docker
import check_container_stats_podman


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
