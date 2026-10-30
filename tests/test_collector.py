import unittest
from observatory.collector import (parse_meminfo, parse_proc_stat, parse_netdev,
                                   cpu_percent, flatten, num)


class CollectorTests(unittest.TestCase):
    def test_cpu_samples_and_zero(self):
        self.assertEqual(cpu_percent((100, 50), (200, 100)), 50.0)
        self.assertEqual(cpu_percent((100, 50), (200, 150)), 0.0)
        self.assertIsNone(cpu_percent(None, (200, 100)))
        self.assertIsNone(cpu_percent((200, 100), (200, 100)))
        self.assertEqual(parse_proc_stat('cpu 1 2 3 4 5 6 7 8 9 10\ncpu0 2 3 4 5\n'),
                         {'cpu': (36, 9), 'cpu0': (14, 5)})

    def test_mem_and_missing(self):
        d=parse_meminfo('MemTotal: 4096000 kB\nMemAvailable: 2048000 kB\nCached: 1024000 kB\n')
        self.assertEqual(d['totalMB'], 4000)
        self.assertEqual(d['usedMB'], 2000)
        self.assertIsNone(parse_meminfo(None)['usedMB'])
        self.assertIsNone(num('nan'))

    def test_netdev(self):
        line=' wlan0: 123 2 0 0 0 0 0 0 456 3 0 0 0 0 0 0'
        self.assertEqual(parse_netdev(line)['wlan0'], (123, 456))
        self.assertEqual(parse_netdev(None), {})

    def test_missing_sensor_is_not_zero(self):
        snap={'cpu':{'usagePercent':None},'memory':{'usedMB':None,'totalMB':None},
              'battery':{'levelPercent':0,'temperatureC':None},
              'network':{'rxMbps':None,'txMbps':0},'storage':[{'usedPercent':None}]}
        self.assertEqual(flatten(snap),{'battery':0.0,'tx':0.0})


if __name__ == '__main__': unittest.main()
