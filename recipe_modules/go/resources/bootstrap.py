# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import contextlib
import errno
import hashlib
import json
import os
import requests
import shutil
import sys
import tarfile
import tempfile
import traceback


GO_URL = 'https://storage.googleapis.com/golang/'
GO_VERSION = 'go1.7'


class InvalidGoError(Exception):
    """Raised by install_go on fatal error."""


@contextlib.contextmanager
def temp_dir(base=None):
    tmpdir = tempfile.mkdtemp(prefix='go', dir=base)
    try:
        yield tmpdir
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)


def install_go(path, platform, version):
    """Installs Go distribution to <path>/go
  
    Args:
        path: root directory to install Go distribution into.
        platform: Go distribution platform, e.g. linux-amd64.
        version: version of Go to install.

    Returns:
        Absolute path to Go distribution.
    """
    version_file = os.path.join(path, 'go', 'VERSION')
    bin_file = os.path.join(path, 'go', 'bin', 'go')

    installed_version = (read_file(version_file) or '').strip()
    if installed_version == version and os.path.exists(bin_file):
        return bin_file, version

    ensure_directory(path)
    with temp_dir(path) as d:
        filename = '%s.%s.tar.gz' % (version, platform)

        temp_file = os.path.join(d, filename)
        fetch_file('%s%s' % (GO_URL, filename), temp_file)
        with tarfile.open(temp_file, 'r:gz') as f:
            f.extractall(d)

        r = requests.get('%s%s.sha256' % (GO_URL, filename))
        if sha256(temp_file) != r.text:
            raise InvalidGoError('Go SHA256 mismatch')

        version_file = os.path.join(d, 'go', 'VERSION')
        installed_version = (read_file(version_file) or '').strip()
        if installed_version != version:
            raise InvalidGoError('Downloaded invalid Go version')

        dstname = os.path.join(path, 'go')
        if os.path.exists(dstname):
            if os.path.isdir(os.path.join(dstname)):
                shutil.rmtree(dstname)
            else:
                os.remove(dstname)
        os.rename(os.path.join(d, 'go'), dstname)

    return bin_file, version


def sha256(filename):
    sha256_hash = hashlib.sha256()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def fetch_file(url, filename):
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=4096):
            f.write(chunk)
    return filename


def ensure_directory(path):
    """Creates a directory."""
    # Handle a case where a file is being converted into a directory.
    chunks = path.split(os.sep)
    for i in xrange(len(chunks)):
        p = os.sep.join(chunks[:i+1])
        if os.path.exists(p) and not os.path.isdir(p):
            os.remove(p)
            break
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def read_file(path):
    """Returns contents of a file or None if missing."""
    try:
        with open(path, 'r') as f:
            return f.read()
    except IOError as e:
        if e.errno == errno.ENOENT:
            return None
        raise


def write_file(path, data):
    """Puts a file on disk, atomically."""
    ensure_directory(os.path.dirname(path))
    fd, temp_file = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, 'w') as f:
        f.write(data)
    os.rename(temp_file, path)


def main():
    parser = argparse.ArgumentParser('bootstrap Go')
    parser.add_argument('--json-output', default=None)
    parser.add_argument('--version', default=GO_VERSION)
    parser.add_argument('--platform', required=True)
    parser.add_argument('--clean', action='store_true',
        help='Clear any existing go distributions, forcing a new download.')
    parser.add_argument('--dest-directory', required=True)
    args = parser.parse_args()

    try:
        exe_path, version = install_go(
            args.dest_directory, args.platform, args.version)
        result = {
            'executable': exe_path,
            'version': version
        }
        if args.json_output:
            with open(args.json_output, 'w') as f:
                json.dump(result, f)
    except Exception as e:
        print 'Exception installing Go: %s' % e
        _exc_type, _exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
