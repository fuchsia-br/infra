# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import re

from recipe_engine import recipe_api

class GitApi(recipe_api.RecipeApi):
    """GitApi provides support for Git."""

    _GIT_HASH_RE = re.compile('[0-9a-f]{40}', re.IGNORECASE)

    def __init__(self, *args, **kwargs):
        super(GitApi, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """Return a git command step."""
        name = kwargs.pop('name', 'git ' + args[0])
        infra_step = kwargs.pop('infra_step', True)
        if 'cwd' not in kwargs:
            kwargs.setdefault('cwd', self.m.path['checkout'])
        git_cmd = ['git']
        options = kwargs.pop('config_options', {})
        for k, v in sorted(options.iteritems()):
            git_cmd.extend(['-c', '%s=%s' % (k, v)])
        return self.m.step(name, git_cmd + list(args), **kwargs)

    def checkout(self, url, ref=None, remote=None, file=None, **kwargs):
        """Checkout a given ref and return the checked out revision."""
        if not ref:
            fetch_ref = self.m.properties.get('branch') or 'master'
            checkout_ref = 'FETCH_HEAD'
        elif self._GIT_HASH_RE.match(ref):
            fetch_ref = ''
            checkout_ref = ref
        elif ref.startswith('refs/heads/'):
            fetch_ref = ref[len('refs/heads/'):]
            checkout_ref = 'FETCH_HEAD'
        else:
            fetch_ref = ref
            checkout_ref = 'FETCH_HEAD'
        fetch_args = [x for x in (remote, fetch_ref) if x]
        self('fetch', *fetch_args, **kwargs)
        if file:
            self('checkout', '-f', checkout_ref, '--', file, **kwargs)
        else:
            self('checkout', '-f', checkout_ref, **kwargs)
        step = self('rev-parse', 'HEAD', stdout=self.m.raw_io.output(),
                    step_test_data=lambda:
                        self.m.raw_io.test_api.stream_output('deadbeef'))
        self('clean', '-f', '-d', '-x', **kwargs)
        return step.stdout.strip()

    def get_hash(self, commit='HEAD', **kwargs):
        """Find and return the hash of the given commit."""
        return self('show', commit, '--format=%H', '-s',
                    step_test_data=lambda:
                        self.m.raw_io.test_api.stream_output('deadbeef'),
                    stdout=self.m.raw_io.output(), **kwargs).stdout.strip()

    def get_timestamp(self, commit='HEAD', test_data=None, **kwargs):
        """Find and return the timestamp of the given commit."""
        return self('show', commit, '--format=%at', '-s',
                    step_test_data=lambda:
                        self.m.raw_io.test_api.stream_output('1473312770'),
                    stdout=self.m.raw_io.output(), **kwargs).stdout.strip()