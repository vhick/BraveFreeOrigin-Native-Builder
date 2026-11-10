#!/usr/bin/env python3
"""Independent ZIP and PE validation. Does not claim real GUI host containment."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile


def pe_info(payload: bytes):
    if len(payload) < 1024 or payload[:2] != b'MZ':
        raise RuntimeError('Not a genuine Windows PE executable')
    off = struct.unpack_from('<I', payload, 60)[0]
    if off > len(payload)-24 or payload[off:off+4] != b'PE\x00\x00':
        raise RuntimeError('PE signature missing')
    machine, sections = struct.unpack_from('<HH', payload, off+4)
    if machine != 0x8664 or sections < 1 or sections > 32:
        raise RuntimeError('Expected real Windows x64 PE executable')
    optional_size = struct.unpack_from('<H',payload,off+20)[0]
    optional = off+24
    if optional+optional_size > len(payload):
        raise RuntimeError('Truncated PE optional header')
    magic = struct.unpack_from('<H',payload,optional)[0]
    if magic not in (0x10b,0x20b):
        raise RuntimeError('Malformed PE optional header')
    directories = optional+(112 if magic == 0x20b else 96)
    if directories+15*8 > optional+optional_size:
        raise RuntimeError('No .NET CLR directory in PE')
    clr_rva, clr_size = struct.unpack_from('<II',payload,directories+14*8)
    if clr_rva == 0 or clr_size < 72:
        raise RuntimeError('No managed .NET CLR header in compiled application')
    # A real compiled assembly must map the CLR directory into its sections.
    section_table = optional+optional_size
    mapped = False
    for i in range(sections):
        loc=section_table+i*40
        if loc+40>len(payload):
            raise RuntimeError('Truncated PE section table')
        virt_size, virt_addr, raw_size, raw_pos = struct.unpack_from('<IIII',payload,loc+8)
        if virt_addr <= clr_rva < virt_addr+max(virt_size,raw_size) and raw_pos < len(payload):
            mapped = True
    if not mapped:
        raise RuntimeError('CLR directory cannot map to real executable sections')
    return machine


def check(package):
    package = Path(package)
    expected_root = 'BraveFreeOrigin-NativePortable/'
    with zipfile.ZipFile(package) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError('ZIP CRC mismatch: '+bad)
        paths = z.namelist()
        normalized = [p.lower() for p in paths]
        if len(normalized) != len(set(normalized)):
            raise RuntimeError('Case-insensitive duplicate ZIP entries')
        for p in paths:
            if not p.startswith(expected_root) or '..' in Path(p).parts or p.startswith('/') or '\\' in p:
                raise RuntimeError('Unsafe or wrong-mode ZIP entry: '+p)
            if any(x in p.lower() for x in ('appinfo.ini', 'traceguard', '.paf.exe', 'bravefreeoriginportable.exe')):
                raise RuntimeError('PortableApps elements forbidden in NATIVE: '+p)
        must = ['BraveFreeOrigin.exe', 'README.txt', 'LICENSES/UPSTREAM-MIT.txt',
                'build-identity.json', 'Data/']
        for name in must:
            if expected_root + name not in paths:
                raise RuntimeError('Missing native entry: ' + name)
        executable = z.read(expected_root + 'BraveFreeOrigin.exe')
        machine = pe_info(executable)
        # Plaintext resource name embedded in the compiled PE's CLR metadata.
        if b'BFO_SOURCE' not in executable:
            raise RuntimeError('Compiled host lacks embedded upstream source resource')
        if not any(p.startswith(expected_root+'locales/') and p.endswith('.json') for p in paths):
            raise RuntimeError('Upstream translation files missing')
        manifest = json.loads(z.read(expected_root+'build-identity.json'))
        if not manifest['upstream_commit'] or len(manifest['upstream_commit']) != 40:
            raise RuntimeError('Invalid upstream commit in manifest')
    hashval = hashlib.sha256(package.read_bytes()).hexdigest()
    print('STATIC-VALIDATED:', package.name)
    print('PE machine:',hex(machine),'embedded upstream source: yes')
    print('Source:',manifest['upstream_release'],manifest['upstream_commit'])
    print('SHA-256:',hashval)
    return hashval

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('zip')
    a=ap.parse_args()
    check(a.zip)
