#!/usr/bin/env python3
"""Resolve only official, published, stable GitHub upstream releases.

Never use main, latest unverified commit, third-party mirrors, or prerelease tags.
`git fetch` verifies Git object consistency; release/tag trust is based on GitHub TLS.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = 'https://api.github.com/repos/TahaHydra/Brave-Free-Origin'
REPO = 'https://github.com/TahaHydra/Brave-Free-Origin.git'
STABLE = re.compile(r'^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')


def semver(tag):
    m = STABLE.fullmatch(tag)
    return tuple(map(int, m.groups())) if m else None


def api_json(url):
    headers = {'Accept': 'application/vnd.github+json',
               'User-Agent': 'BraveFreeOrigin-NativeBuilder-b1r1',
               'X-GitHub-Api-Version': '2022-11-28'}
    token = os.environ.get('GH_TOKEN', '').strip()
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError('Release endpoint 404: not a published stable upstream release: ' + url)
        if e.code in (401, 403, 429):
            raise RuntimeError('GitHub authentication or rate limit failure HTTP ' + str(e.code))
        raise RuntimeError('GitHub API failure HTTP ' + str(e.code) + ': ' + url)


def choose_release(requested):
    if requested != 'latest':
        if semver(requested) is None:
            raise ValueError('Explicit version must be a stable semantic tag like v2.0.2')
        r = api_json(API + '/releases/tags/' + requested)
        if r.get('draft') or r.get('prerelease') or semver(r.get('tag_name', '')) is None:
            raise RuntimeError('Requested release is not stable and published')
        return r
    releases = []
    # A single page normally suffices, but do not assume API returns latest in semantic order.
    for page in range(1, 11):
        chunk = api_json(API + '/releases?per_page=100&page=' + str(page))
        if not isinstance(chunk, list):
            raise RuntimeError('Unexpected GitHub release response')
        releases.extend(r for r in chunk if not r.get('draft') and not r.get('prerelease')
                        and semver(r.get('tag_name', '')) is not None)
        if len(chunk) < 100:
            break
    if not releases:
        raise RuntimeError('No published stable semver upstream release was found')
    return max(releases, key=lambda r: semver(r['tag_name']))


def git(*args):
    p = subprocess.run(['git', *[str(a) for a in args]], text=True, encoding='utf-8',
                       errors='replace', capture_output=True)
    if p.returncode:
        raise RuntimeError('git command failed: ' + ' '.join(map(str, args)) + '\n' + p.stderr)
    return p.stdout.strip()


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blob in iter(lambda: f.read(1024 * 1024), b''):
            h.update(blob)
    return h.hexdigest()


def resolve(version, destination):
    r = choose_release(version)
    tag = r['tag_name']
    if not re.fullmatch(r'v?[0-9]+\.[0-9]+\.[0-9]+', tag):
        raise RuntimeError('Unsafe/non-stable tag')
    dst = Path(destination).absolute()
    if dst.exists() and any(dst.iterdir()):
        raise RuntimeError('Source destination must be empty: ' + str(dst))
    dst.mkdir(parents=True, exist_ok=True)
    git('init', '--quiet', str(dst))
    git('-C', dst, 'remote', 'add', 'origin', REPO)
    git('-C', dst, '-c', 'core.longpaths=true', 'fetch', '--quiet', '--depth=1',
        'origin', 'refs/tags/' + tag)
    git('-C', dst, 'checkout', '--quiet', '--detach', 'FETCH_HEAD')
    sha = git('-C', dst, 'rev-parse', 'HEAD')
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise RuntimeError('Invalid resolved Git commit hash')
    # Compare the immutable local commit to the remotely advertised tag commit.
    remote = git('ls-remote', REPO, 'refs/tags/' + tag, 'refs/tags/' + tag + '^{}')
    points = [line.split()[0] for line in remote.splitlines() if line.endswith('refs/tags/' + tag + '^{}')]
    if not points:
        points = [line.split()[0] for line in remote.splitlines() if line.endswith('refs/tags/' + tag)]
    if len(points) != 1 or points[0].lower() != sha.lower():
        raise RuntimeError('Remote release tag changed or differs from resolved commit')
    paths = ['Brave-Free-Origin.ps1', 'LICENSE', 'tools/Test-App.ps1',
             'tools/Test-Locales.ps1', 'tools/Test-Bootstrap.ps1']
    for rel in paths:
        if not (dst / rel).is_file():
            raise RuntimeError('Required upstream file absent: ' + rel)
    app_source = (dst / 'Brave-Free-Origin.ps1').read_text(encoding='ascii')
    match = re.search(r"(?m)^\$script:AppVersion\s*=\s*'([0-9]+\.[0-9]+\.[0-9]+)'",app_source)
    if not match or match.group(1) != tag.lstrip('v'):
        raise RuntimeError('Application source version does not match official release tag')
    identity = {
        'upstream_repository': REPO,
        'upstream_release': tag,
        'upstream_commit': sha,
        'upstream_source_sha256': digest(dst / 'Brave-Free-Origin.ps1'),
        'license_sha256': digest(dst / 'LICENSE'),
        'dependency_lockfiles': {},
        'builder_revision': 'b1r1',
        'package_revision': 'n1',
        'mode': 'NATIVE',
        'runtime': 'Windows PowerShell 5.1 and .NET Framework 4.x (built into supported Windows)',
    }
    out = Path('work/build_identity.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(identity, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Verified upstream:', tag, sha)
    return identity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='latest')
    parser.add_argument('--destination', default='work/upstream')
    a = parser.parse_args()
    resolve(a.version, a.destination)

if __name__ == '__main__':
    main()
