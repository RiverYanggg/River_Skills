#!/usr/bin/env python3
"""Verify loopback listener, classic VNC auth and an actual raw framebuffer.

Uses Linux libgcrypt through ctypes; no pip dependencies or plaintext password
input. A VNC password file is reversible and must remain private.
"""
import argparse
import ctypes
import ctypes.util
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import zlib


def des(key, data, decrypt=False):
    libname = ctypes.util.find_library('gcrypt')
    if not libname:
        raise RuntimeError('libgcrypt missing: authentication/framebuffer verification not completed')
    lib = ctypes.CDLL(libname)
    lib.gcry_check_version.argtypes = [ctypes.c_char_p]
    lib.gcry_check_version.restype = ctypes.c_char_p
    lib.gcry_check_version(None)
    lib.gcry_cipher_map_name.argtypes = [ctypes.c_char_p]
    lib.gcry_cipher_map_name.restype = ctypes.c_int
    lib.gcry_cipher_open.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    lib.gcry_cipher_setkey.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
    lib.gcry_cipher_close.argtypes = [ctypes.c_void_p]
    operation = lib.gcry_cipher_decrypt if decrypt else lib.gcry_cipher_encrypt
    operation.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    handle = ctypes.c_void_p()
    if len(key) != 8 or len(data) % 8:
        raise ValueError('DES requires an 8-byte key and complete blocks')
    error = lib.gcry_cipher_open(ctypes.byref(handle), lib.gcry_cipher_map_name(b'DES'), 1, 0)
    if error:
        raise RuntimeError('libgcrypt could not initialize DES: ' + str(error))
    try:
        error = lib.gcry_cipher_setkey(handle, key, len(key))
        if error:
            raise RuntimeError('libgcrypt could not set DES key: ' + str(error))
        output = ctypes.create_string_buffer(len(data))
        error = operation(handle, output, len(data), data, len(data))
        if error:
            raise RuntimeError('libgcrypt DES operation failed: ' + str(error))
        return output.raw
    finally:
        lib.gcry_cipher_close(handle)


def listener_addresses(port):
    output = subprocess.run(['ss', '-H', '-ltn', 'sport = :' + str(port)],
                            check=True, capture_output=True, text=True).stdout
    addresses = [line.split()[3] for line in output.splitlines() if line.strip()]
    if not addresses:
        raise RuntimeError('No VNC listener on port ' + str(port))
    for address in addresses:
        if not address.startswith(('127.0.0.1:', '[::1]:', '::1:')):
            raise RuntimeError('VNC exposed beyond loopback: ' + address)
    return addresses


def read_exact(sock, n):
    chunks = bytearray()
    while len(chunks) < n:
        data = sock.recv(n - len(chunks))
        if not data:
            raise RuntimeError('VNC connection closed unexpectedly')
        chunks.extend(data)
    return bytes(chunks)


def save_png(path, width, height, canvas):
    rgb = bytearray(width * height * 3)
    rgb[0::3], rgb[1::3], rgb[2::3] = canvas[2::4], canvas[1::4], canvas[0::4]
    raw = b''.join(b'\0' + rgb[y * width * 3:(y + 1) * width * 3] for y in range(height))

    def chunk(kind, data):
        return (struct.pack('!I', len(data)) + kind + data
                + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff))

    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(png)


def verify(port, password_file, screenshot=None):
    port = int(port)
    if not 1 <= port <= 65535:
        raise ValueError('Invalid VNC port')
    addresses = listener_addresses(port)
    encrypted = Path(password_file).read_bytes()
    if len(encrypted) not in (8, 16):
        raise ValueError('Invalid VNC password file length')
    # Standard VNC password-file obfuscation key, in normal DES bit order.
    password = des(bytes.fromhex('e84ad660c4721ae0'), encrypted[:8], decrypt=True)
    key = bytes(int(format(b, '08b')[::-1], 2) for b in password)
    with socket.create_connection(('127.0.0.1', port), timeout=10) as sock:
        greeting = read_exact(sock, 12)
        if greeting not in (b'RFB 003.008\n', b'RFB 003.007\n'):
            raise RuntimeError('Unsupported protocol banner: ' + repr(greeting))
        sock.sendall(greeting)
        count = read_exact(sock, 1)[0]
        if not count:
            raise RuntimeError('VNC server rejected security negotiation')
        types = list(read_exact(sock, count))
        if 2 not in types or 1 in types:
            raise RuntimeError('Expected password authentication without unauthenticated access: ' + str(types))
        sock.sendall(b'\x02')
        challenge = read_exact(sock, 16)
        sock.sendall(des(key, challenge))
        if struct.unpack('!I', read_exact(sock, 4))[0] != 0:
            raise RuntimeError('VNC authentication failed; do not repeatedly retry a bad password')
        sock.sendall(b'\x01')
        header = read_exact(sock, 24)
        width, height = struct.unpack('!HH', header[:4])
        name_length = struct.unpack('!I', header[20:24])[0]
        if not (0 < width <= 8192 and 0 < height <= 8192 and name_length <= 4096):
            raise RuntimeError('Unexpected framebuffer dimensions/name length')
        name = read_exact(sock, name_length).decode('utf-8', errors='replace')
        # Request 32-bit little-endian BGRX and only raw rectangles.
        sock.sendall(b'\0\0\0\0' + struct.pack('!BBBBHHHBBBxxx', 32, 24, 0, 1, 255, 255, 255, 16, 8, 0))
        sock.sendall(struct.pack('!BBHi', 2, 0, 1, 0))
        sock.sendall(struct.pack('!BBHHHH', 3, 0, 0, 0, width, height))
        canvas = bytearray(width * height * 4) if screenshot else None
        pixels = 0
        for _ in range(30):
            message = read_exact(sock, 1)[0]
            if message == 2:  # bell
                continue
            if message == 3:  # clipboard text
                read_exact(sock, 3)
                length = struct.unpack('!I', read_exact(sock, 4))[0]
                if length > 1048576:
                    raise RuntimeError('Unexpected clipboard size')
                read_exact(sock, length)
                continue
            if message != 0:
                raise RuntimeError('Unexpected VNC message: ' + str(message))
            count = struct.unpack('!H', read_exact(sock, 3)[1:])[0]
            for _ in range(count):
                x, y, rw, rh, encoding = struct.unpack('!HHHHi', read_exact(sock, 12))
                if encoding != 0 or x + rw > width or y + rh > height:
                    raise RuntimeError('Unexpected framebuffer rectangle')
                raw = read_exact(sock, rw * rh * 4)
                pixels += rw * rh
                if canvas is not None:
                    for row in range(rh):
                        start = ((y + row) * width + x) * 4
                        canvas[start:start + rw * 4] = raw[row * rw * 4:(row + 1) * rw * 4]
            if pixels:
                break
        if not pixels:
            raise RuntimeError('Authenticated but no image received')
    if screenshot:
        save_png(Path(screenshot), width, height, canvas)
    return {'listeners': addresses, 'protocol': greeting.decode().strip(),
            'authentication': 'passed', 'desktop': name, 'width': width, 'height': height,
            'received_pixels': pixels, 'screenshot': str(screenshot) if screenshot else None,
            'mac_connection': 'not tested from this server'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('--password-file', required=True, type=Path)
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.port, args.password_file, args.screenshot), indent=2))
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, 'ERROR: ' + str(exc) + '\n')
