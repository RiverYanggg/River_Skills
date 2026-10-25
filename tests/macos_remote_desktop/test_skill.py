import argparse
from contextlib import redirect_stdout
import fcntl
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'skills/macos-remote-desktop/scripts'
sys.path.insert(0, str(SCRIPTS))
import desktop
import verify_vnc


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='desktop-tests-')
        self.root = Path(self.tmp.name)
        self.bin = self.root / 'fake-tools'
        self.bin.mkdir()
        for name in ('Xtigervnc', 'xfce4-session', 'dbus-run-session', 'xdpyinfo', 'google-chrome'):
            self.tool(name, '#!/bin/sh\nexit 0\n')
        self.tool('tigervncpasswd', '#!/usr/bin/env python3\nimport sys\nsys.stdin.buffer.read()\nsys.stdout.buffer.write(b"testtest")\n')
        self.tool('xauth', '#!/usr/bin/env python3\nimport sys,pathlib\np=pathlib.Path(sys.argv[2]);p.write_bytes(b"cookie")\n')
        self.environment = mock.patch.dict(os.environ, {'PATH': str(self.bin) + os.pathsep + os.environ['PATH']})
        self.environment.start()
        self.nonroot = mock.patch.object(desktop.os, 'geteuid', return_value=1000)
        self.nonroot.start()
        self.available = mock.patch.object(desktop, 'free_display', return_value=True)
        self.available.start()
        self.base = self.root / 'private instance %$'
        self.service = self.root / 'units/mac-desktop.service'
        self.helper = self.root / 'bin/mac-desktop'

    def tearDown(self):
        self.available.stop()
        self.nonroot.stop()
        self.environment.stop()
        self.tmp.cleanup()

    def tool(self, name, content):
        p = self.bin / name
        p.write_text(content)
        p.chmod(0o700)

    def args(self, **overrides):
        values = dict(name='mac-desktop', display=None, geometry=None, ssh_target='my-server',
                      proxy=None, no_proxy=False, browser=None, no_browser=False,
                      url=None, xvnc=None, vncpasswd=None, dry_run=False)
        values.update(overrides)
        return argparse.Namespace(**values)

    def configure(self, **overrides):
        with redirect_stdout(io.StringIO()):
            desktop.configure(self.args(**overrides), self.base, self.service, self.helper)

    def test_dry_run_creates_no_files(self):
        self.configure(dry_run=True)
        self.assertFalse(self.base.exists())
        self.assertFalse(self.service.exists())
        self.assertFalse(self.helper.exists())

    def test_idempotent_preserves_password_display_and_helper_execution(self):
        self.configure()
        password = (self.base / 'initial-password.txt').read_bytes()
        config = (self.base / 'config.json').read_bytes()
        self.configure(display=2)
        self.assertEqual(password, (self.base / 'initial-password.txt').read_bytes())
        self.assertEqual(config, (self.base / 'config.json').read_bytes())
        self.assertEqual(subprocess.check_output([self.helper, 'port'], text=True).strip(), '5902')
        self.assertEqual((self.base / 'passwd').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.base.stat().st_mode & 0o777, 0o700)
        self.assertNotIn(password.decode().strip(), config.decode())

    def test_cannot_overwrite_unmanaged_command(self):
        self.helper.parent.mkdir(parents=True)
        self.helper.write_text('my existing program')
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            self.configure()
        self.assertEqual(self.helper.read_text(), 'my existing program')
        self.assertFalse(self.base.exists())

    def test_cannot_reuse_unmanaged_instance_directory(self):
        self.base.mkdir()
        (self.base / 'important.txt').write_text('keep me')
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            self.configure()
        self.assertEqual((self.base / 'important.txt').read_text(), 'keep me')

    def test_active_configuration_change_refused_but_same_config_allowed(self):
        self.configure()
        with (self.base / 'session.lock').open('wb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.configure()
            with self.assertRaisesRegex(ValueError, 'Stop this desktop'):
                self.configure(geometry='1920x1200')
        self.configure(geometry='1920x1200')
        self.assertEqual(json.loads((self.base / 'config.json').read_text())['geometry'], '1920x1200')

    def test_display_change_updates_cookie_and_preserves_password(self):
        self.configure()
        before = (self.base / 'passwd').read_bytes()
        (self.base / 'Xauthority').write_bytes(b'old-cookie')
        self.configure(display=9)
        self.assertEqual((self.base / 'Xauthority').read_bytes(), b'cookie')
        self.assertEqual((self.base / 'passwd').read_bytes(), before)

    def test_saved_service_path_works_inside_isolated_desktop(self):
        self.configure()
        with mock.patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.base / 'config')}):
            info = json.loads(subprocess.check_output([self.helper, 'info'], text=True))
        self.assertEqual(info['service'], str(self.service))

    def test_proxy_credentials_and_shell_target_rejected(self):
        for proxy in ('http://user:secret@localhost:1234', 'http://localhost:1234/path', 'file:///tmp/test'):
            with self.subTest(proxy=proxy), self.assertRaises(ValueError):
                desktop.valid_proxy(proxy)
        for target in ('-oProxyCommand=bad', 'host; touch /tmp/bad', 'ssh my-server', '$(bad)'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                desktop.valid_target(target)
        self.assertEqual(desktop.valid_target('my-server'), 'my-server')

    def test_display_collision_skipped(self):
        with mock.patch.object(desktop, 'free_display', side_effect=lambda d: d == 5):
            self.assertEqual(desktop.choose_display(), 5)
            with self.assertRaises(ValueError):
                desktop.choose_display(2)

    def test_browser_sandbox_kept_and_profile_isolated(self):
        cfg = dict(browser='/usr/bin/google-chrome', proxy=None, url='about:blank')
        args = desktop.browser_args(cfg, self.base)
        self.assertNotIn('--no-sandbox', args)
        self.assertIn('--user-data-dir=' + str(self.base / 'browser-profile'), args)

    def test_no_browser_choice_survives_idempotent_reconfigure(self):
        self.configure(no_browser=True)
        self.configure()
        self.assertIsNone(json.loads((self.base / 'config.json').read_text())['browser'])

    def test_des_known_vector_and_roundtrip(self):
        key = bytes.fromhex('133457799bbcdff1')
        plaintext = bytes.fromhex('0123456789abcdef')
        encrypted = verify_vnc.des(key, plaintext)
        self.assertEqual(encrypted.hex(), '85e813540f0ab405')
        self.assertEqual(verify_vnc.des(key, encrypted, decrypt=True), plaintext)

    def test_public_listener_is_not_accepted(self):
        result = subprocess.CompletedProcess([], 0, stdout='LISTEN 0 5 0.0.0.0:5902 0.0.0.0:*\n')
        with mock.patch.object(verify_vnc.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'beyond loopback'):
                verify_vnc.listener_addresses(5902)


class MacHelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='mac-helper-tests-')
        self.root = Path(self.tmp.name)
        self.log = self.root / 'calls.jsonl'
        self.tools = self.root / 'tools'
        self.tools.mkdir()
        script = '''#!/usr/bin/env python3
import json,os,sys,time
from pathlib import Path
tool=Path(sys.argv[0]).name
with open(os.environ['DESKTOP_TEST_LOG'],'a') as f:
 f.write(json.dumps({'tool':tool,'args':sys.argv[1:],'pid':os.getpid()})+'\\n')
if tool=='uname':print('Darwin')
elif tool=='lsof':sys.exit(0 if os.environ.get('DESKTOP_TEST_OCCUPIED') else 1)
elif tool=='ssh':
 if '-N' in sys.argv:
  if os.environ.get('DESKTOP_TEST_SSH_FAILURE'):sys.exit(1)
  time.sleep(60)
 elif sys.argv[-1].endswith(' port'):print('5907')
elif tool=='nc':print('RFB 003.008')
'''
        for name in ('uname', 'lsof', 'ssh', 'nc', 'open'):
            p = self.tools / name
            p.write_text(script)
            p.chmod(0o700)
        self.env = dict(os.environ, PATH=str(self.tools) + os.pathsep + os.environ['PATH'],
                        DESKTOP_TEST_LOG=str(self.log))

    def tearDown(self):
        self.tmp.cleanup()

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_alias_port_discovery_open_and_owned_tunnel_cleanup(self):
        p = subprocess.Popen(['bash', str(SCRIPTS / 'mac-connect.sh'), 'my-server'],
                             env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            for _ in range(60):
                if any(c['tool'] == 'open' for c in self.calls()):
                    break
                if p.poll() is not None:
                    self.fail('Helper exited before opening desktop: ' + str(p.communicate()))
                time.sleep(.1)
            else:
                self.fail('Helper did not open desktop')
            p.send_signal(signal.SIGINT)
            p.communicate(timeout=5)
            calls = self.calls()
            self.assertEqual(next(c for c in calls if c['tool'] == 'open')['args'], ['vnc://127.0.0.1:15902'])
            tunnel = next(c for c in calls if c['tool'] == 'ssh' and '-N' in c['args'])
            self.assertIn('127.0.0.1:15902:127.0.0.1:5907', tunnel['args'])
            self.assertEqual(tunnel['args'][-1], 'my-server')
            with self.assertRaises(ProcessLookupError):
                os.kill(tunnel['pid'], 0)
        finally:
            if p.poll() is None:
                p.terminate()
                p.communicate(timeout=5)

    def test_occupied_port_does_not_start_ssh(self):
        env = dict(self.env, DESKTOP_TEST_OCCUPIED='1')
        p = subprocess.run(['bash', str(SCRIPTS / 'mac-connect.sh'), 'my-server'],
                           env=env, capture_output=True, text=True, timeout=5)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('already occupied', p.stderr)
        self.assertFalse(any(c['tool'] == 'ssh' for c in self.calls()))

    def test_ssh_failure_does_not_open_screen_sharing(self):
        env = dict(self.env, DESKTOP_TEST_SSH_FAILURE='1')
        p = subprocess.run(['bash', str(SCRIPTS / 'mac-connect.sh'), 'my-server'],
                           env=env, capture_output=True, text=True, timeout=5)
        self.assertNotEqual(p.returncode, 0)
        self.assertTrue(any(c['tool'] == 'ssh' and '-N' in c['args'] for c in self.calls()))
        self.assertFalse(any(c['tool'] == 'open' for c in self.calls()))

    def test_injected_target_rejected_before_external_commands(self):
        p = subprocess.run(['bash', str(SCRIPTS / 'mac-connect.sh'), 'host; false'],
                           env=self.env, capture_output=True, text=True, timeout=5)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(self.calls(), [])


if __name__ == '__main__':
    unittest.main()
