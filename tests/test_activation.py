import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.activate import Adb, ActivationError, complete_snapshot, install_agent, select_device, verify_over_usb


def result(out='', code=0):
    return subprocess.CompletedProcess([], code, out, '')


class ActivationTests(unittest.TestCase):
    def test_selects_s23_without_mutating_s7_or_network_adb(self):
        calls=[]
        class Device:
            def __init__(self, executable, serial=None):
                self.executable,self.serial=executable,serial
            def run(self,args,**kwargs):
                calls.append((self.serial,args))
                if self.serial is None:
                    return result('List of devices attached\nS7USB device usb:1\nS23USB device usb:2\n192.0.2.1:5555 device\nadb-WIRELESS._adb-tls-connect._tcp device\nPENDING unauthorized\n')
                return result({'S7USB':'SM-G935F','S23USB':'SM-S916B'}[self.serial])
        with patch('tools.activate.Adb',Device):
            selected=select_device(Device('adb'))
        self.assertEqual(selected.serial,'S23USB')
        self.assertTrue(all(args in (['devices','-l'],['shell','getprop','ro.product.model']) for _,args in calls))
        self.assertFalse(any(serial=='192.0.2.1:5555' for serial,_ in calls))

    def test_no_matching_phone_fails_before_any_mutation(self):
        class Fake:
            executable='adb'
            def run(self,args):return result('List of devices attached\nPENDING unauthorized\n')
        with self.assertRaises(ActivationError):select_device(Fake())

    def test_corrupt_transfer_never_starts_new_agent(self):
        calls=[]
        class Fake:
            def run(self,args,**kwargs):
                calls.append(args)
                if args[:2]==['shell','sha256sum']:return result('0'*64+' file')
                return result()
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'agent.sh';source.write_text('echo fixture')
            with self.assertRaises(ActivationError):install_agent(Fake(),source)
        self.assertFalse(any('--start' in args or '--stop' in args for args in calls))

    def test_incomplete_stale_and_wrong_device_are_not_success(self):
        data={'device':{'model':'SM-S916B'},'quality':'ok','ageSeconds':1,
              'availability':{'cpu':True,'battery':True,'network':True},'cpu':{'coresPercent':[0]*8}}
        self.assertTrue(complete_snapshot(data))
        data['ageSeconds']=100
        self.assertFalse(complete_snapshot(data))
        data['ageSeconds']=1;data['availability']['network']=False
        self.assertFalse(complete_snapshot(data))
        data['device']['model']='SM-G935F'
        with self.assertRaises(ActivationError):complete_snapshot(data)

    def test_usb_forward_is_removed_after_failure(self):
        calls=[]
        class Fake:
            def run(self,args,**kwargs):calls.append(args);return result('34567')
        with self.assertRaises(ActivationError):verify_over_usb(Fake(),wait_seconds=0)
        self.assertEqual(calls[-1],['forward','--remove','tcp:34567'])


if __name__=='__main__':unittest.main()
