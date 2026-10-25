#!/usr/bin/env python3
"""Run a temporary Xvnc, verify auth/framebuffer, and clean up only this process.

No existing services/profiles are changed. Requires working Xvnc shared libraries
and permission to create local X11 Unix sockets (may need Agent sandbox approval).
"""
import argparse
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
from desktop import choose_display
from verify_vnc import verify


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xvnc', required=True)
    p.add_argument('--vncpasswd', required=True)
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix='skill-vnc-integration-') as temp:
        root = Path(temp)
        password = secrets.token_hex(4)
        secret = root / 'passwd'
        secret.write_bytes(subprocess.run([args.vncpasswd, '-f'], input=(password + '\n').encode(),
                                         check=True, capture_output=True).stdout)
        secret.chmod(0o600)
        # An independent temporary display, not the user's configured desktop.
        display = choose_display()
        with (root / 'vnc.log').open('wb') as log:
            server = subprocess.Popen([args.xvnc, ':' + str(display), '-geometry', '640x480', '-depth', '24',
                '-localhost', 'yes', '-interface', '127.0.0.1', '-rfbport', str(5900 + display),
                '-SecurityTypes', 'VncAuth', '-PasswordFile', str(secret), '-nolisten', 'tcp', '-noreset'],
                stdout=log, stderr=log)
            try:
                for _ in range(50):
                    if server.poll() is not None:
                        raise RuntimeError((root / 'vnc.log').read_text())
                    try:
                        import socket
                        with socket.create_connection(('127.0.0.1', 5900 + display), timeout=.1):
                            break
                    except OSError:
                        time.sleep(.1)
                result = verify(5900 + display, secret, root / 'test.png')
                assert result['received_pixels'] == 640 * 480, result
                assert (root / 'test.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
                assert (root / 'test.png').stat().st_mode & 0o777 == 0o600
                print(json.dumps(result, indent=2))
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
        print('PASS: temporary server, credentials and screenshot cleaned up.')


if __name__ == '__main__':
    main()
