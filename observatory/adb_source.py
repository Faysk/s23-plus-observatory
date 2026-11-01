"""Bounded, session-bound samples from the local Android shell agent."""
import secrets
import time
from pathlib import Path


class AdbSource:
    def __init__(self, directory='/sdcard/Download/s23-observatory-agent'):
        self.directory = Path(directory)
        self.nonce = secrets.token_hex(16)

    def read(self):
        request = self.directory / 'request'
        try:
            self.directory.mkdir(exist_ok=True)
            if request.read_text().strip() != self.nonce:
                pending = self.directory / 'request.tmp'
                pending.write_text(self.nonce + '\n')
                pending.replace(request)
        except FileNotFoundError:
            try:
                request.write_text(self.nonce + '\n')
            except OSError:
                return None
        except OSError:
            return None
        try:
            path = self.directory / 'snapshot'
            with path.open() as stream:
                raw = stream.read(32769)
            if len(raw) > 32768:
                return None
            lines = raw.splitlines()
            if lines[0] != 'S23AGENT1 ' + self.nonce:
                return None
            sections = {}; name = None
            for line in lines[1:]:
                if line.startswith('@'):
                    name = line[1:]; sections[name] = []
                elif name:
                    sections[name].append(line)
            before = float(sections['before'][0])
            after = float(sections['after'][0])
            age = time.clock_gettime(time.CLOCK_BOOTTIME) - after
            if not 0 <= age <= 150 or not .5 <= after - before <= 10:
                return None
            return {key: '\n'.join(value) for key, value in sections.items()} | {
                'ageSeconds': round(age, 1), 'windowSec': round(after - before, 2), 'uptime': after}
        except (OSError, UnicodeError, ValueError, KeyError, IndexError, AttributeError):
            return None
