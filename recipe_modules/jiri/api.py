# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class JiriApi(recipe_api.RecipeApi):
    """JiriApi provides support for Jiri managed checkouts."""

    def __init__(self, *args, **kwargs):
        super(JiriApi, self).__init__(*args, **kwargs)
        self._jiri_executable = None

    def ensure_jiri(self):
        self.m.cipd.install_client()
        jiri_package = ('fuchsia/tools/jiri/%s' %
            self.m.cipd.platform_suffix())
        cipd_dir = self.m.path['cache'].join('cipd')
        self.m.cipd.ensure(cipd_dir, { jiri_package: 'latest' })
        self._jiri_executable = cipd_dir.join('jiri')
        return self._jiri_executable

    @property
    def jiri(self):
        return self._jiri_executable

    def init(self, dir=None, **kwargs):
        assert self._jiri_executable

        cmd = [
            self._jiri_executable,
            'init',
        ]
        if dir:
            cmd.append(dir)

        return self.m.step('init', cmd)

    def update(self, gc=False, manifest=None, **kwargs):
        assert self._jiri_executable

        cmd = [
            self._jiri_executable,
            'update', '-autoupdate=false',
        ]
        if gc:
            cmd.extend(['-gc=true'])
        if manifest:
            cmd.extend(['-manifest=%s' % manifest]) 

        return self.m.step('update', cmd)

    def clean_project(self, branches=False, **kwargs):
        assert self._jiri_executable

        cmd = [
            self._jiri_executable,
            'project', 'clean'
        ]
        if branches:
            cmd.extend(['-branches=true'])

        return self.m.step('project clean', cmd)

    def import_manifest(self, manifest, remote, overwrite=False, **kwargs):
        assert self._jiri_executable

        cmd = [
            self._jiri_executable,
            'import',
        ]
        if overwrite:
            cmd.extend(['-overwrite=true'])
        cmd.extend([manifest, remote])

        return self.m.step('import', cmd)

    def patch(self, ref, host=None, delete=False, force=False, **kwargs):
        assert self._jiri_executable

        cmd = [
            self._jiri_executable,
            'cl', 'patch'
        ]
        if host:
            cmd.extend(['-host', host])
        if delete:
            cmd.extend(['-delete=true'])
        if force:
            cmd.extend(['-force=true'])
        cmd.extend([ref])

        return self.m.step('patch', cmd)
