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
import tempfile
import time
import traceback


# Default package repository URL.
CIPD_BACKEND_URL = 'https://chrome-infra-packages.appspot.com'


class CipdBootstrapError(Exception):
    """Raised by install_cipd_client on fatal error."""


@contextlib.contextmanager
def temp_dir(base):
    tmpdir = tempfile.mkdtemp(prefix='cipd', dir=base)
    try:
        yield tmpdir
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)


def install_cipd_client(path, platform, version):
    """Installs CIPD client to <path>/cipd.

    Args:
        path: root directory to install CIPD client into.
        platform: cipd client package platform, e.g. linux-amd64.
        version: version of the package to install.

    Returns:
        Absolute path to CIPD executable.
    """
    package = 'infra/tools/cipd/%s' % platform

    version_file = os.path.join(path, 'VERSION')
    bin_file = os.path.join(path, 'cipd')

    # Resolve version to concrete instance ID, e.g "live" -> "abcdef0123....".
    instance_id = call_cipd_api(
        'repo/v1/instance/resolve',
        {'package_name': package, 'version': version})['instance_id']

    installed_instance_id = (read_file(version_file) or '').strip()
    if installed_instance_id == instance_id and os.path.exists(bin_file):
        return bin_file, instance_id

    # Resolve instance ID to an URL to fetch client binary from.
    client_info = call_cipd_api(
        'repo/v1/client',
        {'package_name': package, 'instance_id': instance_id})

    ensure_directory(path)
    with temp_dir(path) as d:
        temp_bin_file = os.path.join(d, 'cipd')
        fetch_file(client_info['client_binary']['fetch_url'], temp_bin_file)

        if sha1(temp_bin_file) != client_info['client_binary']['sha1']:
            raise CipdBootstrapError('Client SHA1 mismatch')
        
        os.rename(temp_bin_file, bin_file)
        os.chmod(bin_file, 0755)

        write_file(version_file, instance_id + '\n')

    return bin_file, instance_id


def call_cipd_api(endpoint, query):
    """Sends GET request to CIPD backend, parses JSON response."""
    url = '%s/_ah/api/%s' % (CIPD_BACKEND_URL, endpoint)
    r = requests.get(url, params=query)
    r.raise_for_status()
    body = r.json()
    status = body.get('status')
    if status != 'SUCCESS':
        m = body.get('error_message') or '<no error message>'
        raise CipdBootstrapError('Server replied with error %s: %s' % (status, m))
    return body


def sha1(filename):
    sha1_hash = hashlib.sha1()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha1_hash.update(chunk)
    return sha1_hash.hexdigest()


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


def dump_json(obj):
  """Pretty-formats object to JSON."""
  return json.dumps(obj, indent=2, sort_keys=True, separators=(',',':'))


def main():
    parser = argparse.ArgumentParser('bootstrap cipd')
    parser.add_argument('--json-output', default=None)
    parser.add_argument('--version', default='latest')
    parser.add_argument('--platform', required=True)
    parser.add_argument('--dest-directory', required=True)
    args = parser.parse_args()

    try:
        exe_path, instance_id = install_cipd_client(args.dest_directory,
                                                    args.platform, args.version)
        result = {
            'executable': exe_path,
            'instance_id': instance_id
        }
        if args.json_output:
            with open(args.json_output, 'w') as f:
                json.dump(result, f)
    except Exception as e:
        print 'Exception installing cipd: %s' % e
        _exc_type, _exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
