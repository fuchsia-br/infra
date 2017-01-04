# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import errno
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
import urllib
import urllib2


# CIPD client endpoint.
CIPD_CLIENT_URL = 'https://chrome-infra-packages.appspot.com/client'

# CIPD client default version.
CIPD_CLIENT_VERSION = 'git_revision:05844bd9d1200cba8449b936b76e25eb90eabe25'


class CipdBootstrapError(Exception):
    """Raised by install_cipd_client on fatal error."""


def install_cipd_client(path, platform, version):
    """Installs CIPD client to <path>/cipd.

    Args:
        path: root directory to install CIPD client into.
        platform: cipd client package platform, e.g. linux-amd64.
        version: version of the package to install.

    Returns:
        Absolute path to CIPD executable.
    """
    cipd_path = os.path.join(path, 'cipd')

    if not os.path.exists(cipd_path):
        status, data = fetch_url(
            CIPD_CLIENT_URL,
            {'platform': platform, 'version': version})
        if status != 200:
            print 'Failed to fetch client binary, HTTP %d' % status
            raise CipdBootstrapError('Failed to fetch client binary, HTTP %d' % status)
        write_file(cipd_path, data)
        os.chmod(cipd_path, 0755)

    if subprocess.call([cipd_path, 'selfupdate', '-version', version]) != 0:
        print 'Failed to selfupdate the client'
        raise CipdBootstrapError('Failed to selfupdate the client')

    return cipd_path


def fetch_url(url, params=None):
    """Sends GET request (with retries).
    Args:
        url: URL to fetch.
        params: Optional dictionary with request params.
    Returns:
        (200, reply body) on success.
        (HTTP code, None) on HTTP 401, 403, or 404 reply.
    Raises:
        Whatever urllib2 raises.
    """
    if params:
        url += '?' + urllib.urlencode(params)
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'cipd recipe bootstrap.py')
    i = 0
    while True:
        i += 1
        try:
            return 200, urllib2.urlopen(req, timeout=60).read()
        except Exception as e:
            if isinstance(e, urllib2.HTTPError):
                print 'Failed to fetch %s, server returned HTTP %d' % (url, e.code)
                if e.code in (401, 403, 404):
                    return e.code, None
            else:
                print 'Failed to fetch %s' % url
            if i == 20:
                raise
        print 'Retrying in %d sec.' % i
        time.sleep(i)


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
    parser = argparse.ArgumentParser('bootstrap cipd')
    parser.add_argument('--json-output', default=None)
    parser.add_argument('--version', default=None)
    parser.add_argument('--platform', required=True)
    parser.add_argument('--dest-directory', required=True)
    args = parser.parse_args()

    version = args.version or CIPD_CLIENT_VERSION

    try:
        exe_path = install_cipd_client(args.dest_directory,
                                       args.platform, version)
        result = {
            'executable': exe_path,
            'version': version,
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
