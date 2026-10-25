#!/usr/bin/env python3
"""Test generated configuration + XFCE + Chrome in a temporary user unit.

Requires systemd user manager, XFCE, x11-utils and an installed Chrome/Chromium.
Creates a unique transient unit and removes it, its files, and its process group.
Does not change the user's existing desktop/services or enable lingering.
"""
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

SCRIPTS = Path(__file__).resolve().parents[2] / 'skills/macos-remote-desktop/scripts'
sys.path.insert(0, str(SCRIPTS))
import desktop
from verify_vnc import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xvnc', required=True)
    parser.add_argument('--vncpasswd', required=True)
    parser.add_argument('--browser', required=True)
    args = parser.parse_args()
    name = 'skill-desktop-test-' + secrets.token_hex(4)
    with tempfile.TemporaryDirectory(prefix='skill-desktop-integration-') as temp:
        root = Path(temp)
        base, service, helper = root / 'instance', root / (name + '.service'), root / 'bin' / name
        config_args = argparse.Namespace(name=name, display=None, geometry='800x600', ssh_target='example-server',
            proxy=None, no_proxy=True, browser=args.browser, no_browser=False, url='about:blank',
            xvnc=args.xvnc, vncpasswd=args.vncpasswd, dry_run=False)
        with redirect_stdout(io.StringIO()):
            desktop.configure(config_args, base, service, helper)
            original_password = (base / 'passwd').read_bytes()
            desktop.configure(config_args, base, service, helper)
            assert original_password == (base / 'passwd').read_bytes()
        cfg = desktop.load(base)
        env = dict(os.environ, DISPLAY=':' + str(cfg['display']), XAUTHORITY=str(base / 'Xauthority'))
        subprocess.run(['systemd-analyze', '--user', 'verify', str(service)], check=True)
        started = False
        try:
            subprocess.run(['systemd-run', '--user', '--unit=' + name, '--collect',
                '--property=KillMode=control-group', '--property=TimeoutStopSec=15',
                sys.executable, str(base / 'desktop.py'), '--name', name, '--base', str(base), 'session'], check=True)
            started = True
            for _ in range(100):
                tree = subprocess.run(['xwininfo', '-root', '-tree'], env=env, capture_output=True, text=True)
                wm = subprocess.run(['xprop', '-root', '_NET_SUPPORTING_WM_CHECK'], env=env,
                                    capture_output=True, text=True)
                if tree.returncode == 0 and 'Google Chrome' in tree.stdout and 'window id #' in wm.stdout:
                    break
                time.sleep(.2)
            else:
                raise RuntimeError('XFCE/Chrome window not detected: ' + (base / 'logs/session.log').read_text()[-4000:])
            result = verify(cfg['port'], base / 'passwd', root / 'screen.png')
            assert result['received_pixels'] == 800 * 600
            result['xfce_window_manager'] = 'detected via X11 root property'
            result['chrome_window'] = 'detected via X11 window tree'
            print(json.dumps(result, indent=2))
        finally:
            if started:
                subprocess.run(['systemctl', '--user', 'stop', name + '.service'], check=True)
        assert not desktop.instance_running(base)
        print('PASS: temporary XFCE/Chrome unit, process group and files cleaned up.')


if __name__ == '__main__':
    main()
