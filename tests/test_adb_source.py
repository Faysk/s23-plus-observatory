import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from observatory.adb_source import AdbSource
from observatory.collector import battery_from_android, cpu_percent, parse_proc_stat


class AndroidSourceTests(unittest.TestCase):
    def setUp(self):
        boot = patch('observatory.adb_source.time.CLOCK_BOOTTIME', 7, create=True)
        boot.start()
        self.addCleanup(boot.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = AdbSource(self.tmp.name)
        self.source.read()

    def sample(self, nonce=None, before=98, after=99, suffix=''):
        Path(self.tmp.name, 'snapshot').write_text(
            f'S23AGENT1 {nonce or self.source.nonce}\n@before\n{before}\n'
            f'@cpu_before\ncpu 10 0 0 10\n@after\n{after}\n'
            '@cpu_after\ncpu 20 0 0 20\n' + suffix)

    @patch('observatory.adb_source.time.clock_gettime', return_value=100, create=True)
    def test_fresh_session_and_cpu_window(self, _):
        self.sample()
        data = self.source.read()
        self.assertEqual(data['ageSeconds'], 1)
        self.assertEqual(data['windowSec'], 1)
        a = parse_proc_stat(data['cpu_before'])['cpu']
        b = parse_proc_stat(data['cpu_after'])['cpu']
        self.assertEqual(cpu_percent(a, b), 50)

    @patch('observatory.adb_source.time.clock_gettime', return_value=300, create=True)
    def test_reject_stale_wrong_session_and_oversize(self, _):
        self.sample()
        self.assertIsNone(self.source.read())
        self.sample(nonce='0' * 32, before=298, after=299)
        self.assertIsNone(self.source.read())
        self.sample(before=298, after=299, suffix='x' * 32769)
        self.assertIsNone(self.source.read())

    @patch('observatory.adb_source.time.clock_gettime', return_value=100, create=True)
    def test_reject_future_and_invalid_window(self, _):
        for before, after in [(101, 102), (90, 99), (99, 99), ('nan', 99)]:
            self.sample(before=before, after=after)
            # A nine-second window is allowed; the other samples are rejected.
            if before == 90:
                self.assertIsNotNone(self.source.read())
            else:
                self.assertIsNone(self.source.read())

    def test_battery_units_and_missing_data(self):
        data = battery_from_android('  level: 47\n  scale: 100\n  temperature: 325\n'
                                    '  voltage: 4210\n  status: 2\n  health: 2\n  USB powered: true')
        self.assertEqual(data['levelPercent'], 47)
        self.assertEqual(data['temperatureC'], 32.5)
        self.assertEqual(data['voltageMV'], 4210)
        self.assertEqual(data['plugged'], 'USB')
        self.assertIsNone(battery_from_android('')['levelPercent'])
        self.assertIsNone(battery_from_android('')['plugged'])
        self.assertIsNone(cpu_percent((100, 20), (110, 40)))


if __name__ == '__main__':
    unittest.main()
