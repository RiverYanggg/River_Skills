"""Observable shell behavior; no real network, accounts, or service mutations."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'skills/server-mihomo-codex/scripts/proxycheck.sh'


class ProxyCheckTests(unittest.TestCase):
    def run_check(self, country='US', expected='US', fail=False, invoke=True):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / 'curl'
            fake.write_text('''#!/bin/bash
printf '%s\\n' "$*" >> "$CALL_LOG"
if [ "$CURL_FAIL" = 1 ]; then exit 28; fi
printf 'ip=192.0.2.1\\nloc=%s\\r\\n' "$COUNTRY"
''')
            fake.chmod(0o755)
            env = dict(os.environ, PATH=tmp + os.pathsep + os.environ['PATH'],
                       COUNTRY=country, MIHOMO_EXPECTED_COUNTRY=expected,
                       MIHOMO_PROXY_URL='http://127.0.0.1:23456',
                       CURL_FAIL='1' if fail else '0', CALL_LOG=str(root / 'calls'))
            result = subprocess.run(['bash', '-c', '. "$1"; ' + ('proxycheck' if invoke else ':') ,
                                     'test', str(SCRIPT)], env=env, capture_output=True, text=True)
            calls = (root / 'calls').read_text().splitlines() if (root / 'calls').exists() else []
            return result, calls

    def test_us_and_explicit_proxy(self):
        result, calls = self.run_check()
        self.assertEqual(result.returncode, 0)
        self.assertIn('US ✓', result.stdout)
        self.assertEqual(len(calls), 1)
        self.assertIn('--proxy http://127.0.0.1:23456 --noproxy  --connect-timeout 3 --max-time 5', calls[0])

    def test_other_country_reports_connected_but_mismatch(self):
        result, calls = self.run_check(country='JP')
        self.assertEqual(result.returncode, 1)
        self.assertIn('JP（期望 US）', result.stderr)
        self.assertEqual(len(calls), 1)

    def test_any_country_if_no_preference(self):
        result, _ = self.run_check(country='JP', expected='')
        self.assertEqual(result.returncode, 0)
        self.assertIn('JP ✓', result.stdout)

    def test_timeout_retries_three_times(self):
        result, calls = self.run_check(fail=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(calls), 3)
        self.assertIn('超时', result.stderr)

    def test_invalid_country_not_success(self):
        result, calls = self.run_check(country='<html>')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(calls), 3)

    def test_noninteractive_source_is_quiet(self):
        result, calls = self.run_check(invoke=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout + result.stderr, '')
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
