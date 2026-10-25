#!/usr/bin/env python3
"""Per-user XFCE/TigerVNC instance management. Never installs system packages."""
import argparse
import fcntl
import json
import os
import pwd
from pathlib import Path
import re
import secrets
import shlex
import shutil
import signal
import socket
import string
import subprocess
import sys
import time
from urllib.parse import urlsplit

MARKER = '# Managed by macos-remote-desktop skill.'
SCHEMA = 'macos-remote-desktop/v1'


def paths(name):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', name):
        raise ValueError('Instance name must match [a-z][a-z0-9-]{0,39}')
    home = Path.home()
    data = Path(os.environ.get('XDG_DATA_HOME') or home / '.local/share')
    config = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    return (data / 'macos-remote-desktop' / name,
            config / 'systemd/user' / (name + '.service'),
            home / '.local/bin' / name)


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def atomic_write(path, content, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + secrets.token_hex(6) + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content.encode() if isinstance(content, str) else content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def executable(explicit, candidates):
    if explicit:
        p = shutil.which(explicit)
        if not p:
            raise ValueError('Executable not found: ' + explicit)
        return str(Path(p).absolute())
    return next((str(Path(p).absolute()) for c in candidates
                 if (p := shutil.which(str(c)))), None)


def valid_target(value):
    # A destination, not a shell command. SSH options belong in ~/.ssh/config.
    if value and not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@:\[\]-]*', value):
        raise ValueError('Use an SSH alias or user@host; put SSH options in ~/.ssh/config')
    return value


def valid_proxy(value):
    if not value:
        return None
    u = urlsplit(value)
    if u.scheme not in ('http', 'https', 'socks4', 'socks5') or not u.hostname:
        raise ValueError('Proxy must be an http(s)/socks4/socks5 URL')
    if u.username is not None or u.password is not None:
        raise ValueError('Do not store proxy credentials in config or process arguments')
    if u.path not in ('', '/') or u.query or u.fragment or any(c.isspace() for c in value):
        raise ValueError('Proxy URL must contain only scheme, host and optional port')
    _ = u.port
    return value


def free_display(display):
    if not 1 <= display <= 99:
        return False
    if Path('/tmp/.X%d-lock' % display).exists() or Path('/tmp/.X11-unix/X%d' % display).exists():
        return False
    try:
        with socket.socket() as s:
            s.bind(('127.0.0.1', 5900 + display))
        return True
    except OSError:
        return False


def choose_display(requested=None):
    if requested is not None:
        if not free_display(requested):
            raise ValueError('Display or VNC port occupied: :' + str(requested))
        return requested
    for d in range(2, 100):
        if free_display(d):
            return d
    raise ValueError('No free display/port pair found in :2..:99')


def load(base):
    cfg = json.loads((base / 'config.json').read_text())
    if cfg.get('schema') != SCHEMA or cfg.get('uid') != os.getuid():
        raise ValueError('Configuration does not belong to this skill/current user')
    return cfg


def managed_write(path, content, mode=0o600):
    if path.exists() and MARKER not in path.read_text():
        raise ValueError('Refusing to overwrite unmanaged file: ' + str(path))
    atomic_write(path, content, mode)


def unit_quote(value):
    # systemd command syntax, not shell syntax. Also escape specifiers.
    return '"' + str(value).replace('%', '%%').replace('$', '$$').replace('\\', '\\\\').replace('"', '\\"') + '"'


def instance_running(base):
    lock = base / 'session.lock'
    if not lock.exists():
        return False
    with lock.open('rb') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return False
        except BlockingIOError:
            return True


def configure(args, base, service, helper):
    if sys.platform != 'linux' or os.geteuid() == 0:
        raise ValueError('Configure on Linux as the intended non-root desktop user')
    old = load(base) if (base / 'config.json').exists() else {}
    runtime = base.parent / 'runtime/usr/bin'
    cfg = dict(old)
    cfg.update(schema=SCHEMA, uid=os.getuid(), user=pwd.getpwuid(os.getuid()).pw_name, name=args.name)
    if old and args.display in (None, old['display']):
        cfg['display'] = old['display']
    else:
        cfg['display'] = choose_display(args.display)
    service = Path(old.get('service_path', service))
    helper = Path(old.get('helper_path', helper))
    cfg['service_path'], cfg['helper_path'] = str(service), str(helper)
    cfg['port'] = 5900 + cfg['display']
    cfg['geometry'] = args.geometry or old.get('geometry', '1600x1000')
    m = re.fullmatch(r'(\d{3,5})x(\d{3,5})', cfg['geometry'])
    if not m or any(not 320 <= int(v) <= 8192 for v in m.groups()):
        raise ValueError('Geometry must be WIDTHxHEIGHT, each dimension between 320 and 8192')
    cfg['ssh_target'] = valid_target(args.ssh_target if args.ssh_target is not None else old.get('ssh_target'))
    cfg['proxy'] = valid_proxy(args.proxy if args.proxy is not None else old.get('proxy'))
    if args.no_proxy:
        cfg['proxy'] = None
    candidates = {
        'xvnc': ['Xtigervnc', 'Xvnc', runtime / 'Xtigervnc'],
        'vncpasswd': ['tigervncpasswd', 'vncpasswd', runtime / 'tigervncpasswd'],
        'desktop': ['xfce4-session'], 'dbus': ['dbus-run-session'],
        'xauth': ['xauth'], 'xdpyinfo': ['xdpyinfo'],
    }
    for key, options in candidates.items():
        cfg[key] = executable(getattr(args, key, None) or old.get(key), options)
    missing = [k for k in candidates if not cfg[k]]
    if missing:
        raise ValueError('Missing dependencies: ' + ', '.join(missing) + '; read references/server-setup.md')
    if args.no_browser or (old and args.browser is None and old.get('browser') is None):
        cfg['browser'] = None
    else:
        cfg['browser'] = executable(args.browser or old.get('browser'),
                                    ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'firefox'])
    if cfg['proxy'] and cfg['browser'] and 'firefox' in Path(cfg['browser']).name:
        raise ValueError('For Firefox, configure proxy manually in its isolated profile; omit --proxy')
    cfg['url'] = args.url or old.get('url', 'about:blank')
    if not (cfg['url'] == 'about:blank' or cfg['url'].startswith(('https://', 'http://'))):
        raise ValueError('Start URL must be about:blank or http(s)')
    if urlsplit(cfg['url']).username is not None or urlsplit(cfg['url']).password is not None:
        raise ValueError('Do not embed website credentials in the browser start URL')
    if any(c in str(base) + str(service) + str(helper) for c in '\n\r'):
        raise ValueError('Newlines in installation paths are unsupported')
    manager = base / 'desktop.py'
    unit = (MARKER + '\n[Unit]\nDescription=Personal XFCE desktop (' + args.name + ')\n'
            '[Service]\nType=simple\nExecStart=' + unit_quote(sys.executable) + ' ' + unit_quote(manager)
            + ' --name ' + args.name + ' --base ' + unit_quote(base) + ' session\n'
            'Restart=on-failure\nRestartSec=5\nKillMode=control-group\nTimeoutStopSec=15\n'
            '[Install]\nWantedBy=default.target\n')
    launcher = ('#!/bin/sh\n' + MARKER + '\nexec ' + shlex.join(
        [sys.executable, str(manager), '--name', args.name, '--base', str(base)]) + ' "$@"\n')
    for p in (service, helper):
        if p.exists() and MARKER not in p.read_text():
            raise ValueError('Refusing to overwrite unmanaged file: ' + str(p))
    if old and cfg != old and instance_running(base):
        raise ValueError('Stop this desktop before changing its configuration; save open applications first')
    if args.dry_run:
        print(json.dumps({'configuration': cfg, 'base': str(base), 'service': str(service),
                          'helper': str(helper), 'starts_service': False}, ensure_ascii=False, indent=2))
        return
    if base.exists() and any(base.iterdir()) and not old:
        raise ValueError('Refusing to reuse a nonempty directory without this skill configuration: ' + str(base))
    base.mkdir(parents=True, exist_ok=True)
    base.chmod(0o700)
    for directory in ('config', 'cache', 'logs', 'browser-profile'):
        (base / directory).mkdir(exist_ok=True)
    for script in ('desktop.py', 'verify_vnc.py'):
        source = Path(__file__).with_name(script)
        if source.resolve() != (base / script).resolve():
            atomic_write(base / script, source.read_bytes(), 0o700)
    if not (base / 'passwd').exists():
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        encoded = run([cfg['vncpasswd'], '-f'], input=(password + '\n').encode(), capture_output=True).stdout
        if len(encoded) != 8:
            raise ValueError('vncpasswd produced unexpected output')
        atomic_write(base / 'passwd', encoded)
        atomic_write(base / 'initial-password.txt', password + '\n')
    (base / 'passwd').chmod(0o600)
    if (base / 'initial-password.txt').exists():
        (base / 'initial-password.txt').chmod(0o600)
    if not (base / 'Xauthority').exists():
        atomic_write(base / 'Xauthority', b'')
    if old.get('display') != cfg['display'] or not (base / 'Xauthority').stat().st_size:
        run([cfg['xauth'], '-f', base / 'Xauthority', 'add', ':' + str(cfg['display']),
             'MIT-MAGIC-COOKIE-1', secrets.token_hex(16)], capture_output=True)
    (base / 'Xauthority').chmod(0o600)
    atomic_write(base / 'config.json', json.dumps(cfg, ensure_ascii=False, indent=2) + '\n')
    managed_write(service, unit)
    managed_write(helper, launcher, 0o700)
    print('Configured:', base)
    print('Control command:', helper)
    print('Start:', shlex.quote(str(helper)), 'start')
    if not cfg['browser']:
        print('Browser not configured; install/select one before claiming browser readiness.')


def browser_args(cfg, base):
    browser = cfg.get('browser')
    if not browser:
        return None
    if 'firefox' in Path(browser).name:
        return [browser, '--no-remote', '--profile', str(base / 'browser-profile'), cfg['url']]
    args = [browser, '--user-data-dir=' + str(base / 'browser-profile'),
            '--no-first-run', '--no-default-browser-check']
    if cfg.get('proxy'):
        args.append('--proxy-server=' + cfg['proxy'])
    return args + [cfg['url']]


def session(cfg, base):
    lock_fd = os.open(base / 'session.lock', os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lock_fd)
        raise RuntimeError('This desktop instance is already running')
    env = os.environ.copy()
    env.update(DISPLAY=':' + str(cfg['display']), XAUTHORITY=str(base / 'Xauthority'),
               XDG_CONFIG_HOME=str(base / 'config'), XDG_CACHE_HOME=str(base / 'cache'),
               XDG_SESSION_TYPE='x11', XDG_CURRENT_DESKTOP='XFCE')
    for key in ('SESSION_MANAGER', 'DBUS_SESSION_BUS_ADDRESS', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    # Do not import SSH/Agent proxy environment as an implicit browser setting.
    for key in list(env):
        if key.lower() in ('http_proxy', 'https_proxy', 'all_proxy', 'ftp_proxy'):
            env.pop(key)
    processes = []
    stopping = False

    def stop(signum=None, frame=None):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with (base / 'logs/vnc.log').open('ab') as vlog, (base / 'logs/session.log').open('ab') as dlog:
        try:
            vnc = subprocess.Popen([cfg['xvnc'], env['DISPLAY'], '-geometry', cfg['geometry'], '-depth', '24',
                '-desktop', cfg['name'], '-localhost', 'yes', '-interface', '127.0.0.1',
                '-rfbport', str(cfg['port']), '-SecurityTypes', 'VncAuth', '-PasswordFile', str(base / 'passwd'),
                '-auth', env['XAUTHORITY'], '-nolisten', 'tcp', '-AlwaysShared', '-noreset'],
                env=env, stdout=vlog, stderr=vlog, start_new_session=True)
            processes.append(vnc)
            for _ in range(50):
                if stopping or vnc.poll() is not None:
                    raise RuntimeError('VNC exited during startup; inspect logs/vnc.log')
                if subprocess.run([cfg['xdpyinfo']], env=env, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, timeout=2).returncode == 0:
                    break
                time.sleep(.2)
            else:
                raise RuntimeError('X display did not become ready')
            desktop = subprocess.Popen([cfg['dbus'], '--', cfg['desktop']], env=env,
                stdout=dlog, stderr=dlog, start_new_session=True)
            processes.append(desktop)
            for _ in range(15):
                if desktop.poll() is not None or stopping:
                    break
                time.sleep(.2)
            cmd = browser_args(cfg, base)
            if cmd and desktop.poll() is None and not stopping:
                processes.append(subprocess.Popen(cmd, env=env, stdout=dlog, stderr=dlog,
                                                  start_new_session=True))
            while not stopping and desktop.poll() is None and vnc.poll() is None:
                time.sleep(.5)
            if not stopping and (vnc.poll() is not None or desktop.poll() not in (None, 0)):
                raise RuntimeError('Desktop/VNC stopped unexpectedly; inspect instance logs')
        finally:
            for p in reversed(processes):
                if p.poll() is None:
                    try:
                        os.killpg(p.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            deadline = time.monotonic() + 8
            for p in reversed(processes):
                try:
                    p.wait(timeout=max(.1, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    p.wait()
            os.close(lock_fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='mac-desktop', help='Instance/control-command name')
    parser.add_argument('--base', type=Path, help=argparse.SUPPRESS)
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('configure', help='Prepare files; does not install packages or start services')
    for option in ('ssh-target', 'geometry', 'browser', 'proxy', 'url', 'xvnc', 'vncpasswd'):
        p.add_argument('--' + option)
    p.add_argument('--display', type=int)
    p.add_argument('--no-browser', action='store_true')
    p.add_argument('--no-proxy', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    for cmd in ('start', 'stop', 'restart', 'status', 'session', 'password', 'change-password', 'port', 'info'):
        subs.add_parser(cmd)
    p = subs.add_parser('verify')
    p.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    base, service, helper = paths(args.name)
    if args.base:
        base = args.base.absolute()
    if args.command == 'configure':
        configure(args, base, service, helper)
        return
    cfg = load(base)
    service = Path(cfg['service_path'])
    if args.command == 'session':
        session(cfg, base)
    elif args.command in ('start', 'stop', 'restart', 'status'):
        if args.command == 'start':
            run(['systemctl', '--user', 'daemon-reload'])
            run(['systemctl', '--user', 'enable', '--now', service.name])
        else:
            run(['systemctl', '--user', args.command, service.name])
    elif args.command == 'port':
        print(cfg['port'])
    elif args.command == 'info':
        print(json.dumps({**cfg, 'base': str(base), 'service': str(service),
                          'helper': str(helper)}, indent=2, ensure_ascii=False))
    elif args.command == 'password':
        p = base / 'initial-password.txt'
        if not p.exists():
            raise ValueError('Initial password no longer stored; use change-password to set a new one')
        print(p.read_text().strip())
    elif args.command == 'change-password':
        temporary = base / ('passwd.' + secrets.token_hex(6))
        try:
            run([cfg['vncpasswd'], temporary])
            temporary.chmod(0o600)
            if len(temporary.read_bytes()) not in (8, 16):
                raise ValueError('Unexpected VNC password file')
            os.replace(temporary, base / 'passwd')
            (base / 'initial-password.txt').unlink(missing_ok=True)
            print('Password updated; VNC reads it on the next connection. No desktop restart needed.')
        finally:
            temporary.unlink(missing_ok=True)
    elif args.command == 'verify':
        from verify_vnc import verify
        print(json.dumps(verify(cfg['port'], base / 'passwd', args.screenshot), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
