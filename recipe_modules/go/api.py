# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class GoApi(recipe_api.RecipeApi):
    """GoApi provides support for Go."""

    def __init__(self, *args, **kwargs):
        super(GoApi, self).__init__(*args, **kwargs)
        self._go_executable = None
        self._go_version = None

    def platform_suffix(self):
        """Use to get distribution for the correct platform."""
        return '%s-%s' % (
            self.m.platform.name.replace('mac', 'darwin'),
            {
                32: '386',
                64: 'amd64',
            }[self.m.platform.bits],
        )

    def install_go(self, step_name='install go', version=None):
        """Ensures that go distribution is installed."""
        assert version is None or version.startswith('go')
        step = self.m.python(
                name=step_name,
                script=self.resource('bootstrap.py'),
                args=[
                    '--platform', self.platform_suffix(),
                    '--dest-directory', self.m.path['slave_build'].join('go'),
                    '--json-output', self.m.json.output(),
                ] +
                (['--version', version] if version else []),
                step_test_data=lambda: self.test_api.example_install_go(version)
            )
        self._go_executable = step.json.output['executable']
        step.presentation.step_text = (
                'Go version: %s' % step.json.output['version'])
        return step

    def get_executable(self):
        return self._go_executable

    def build(self, packages, ldflags=None, install=False,
              force=False, output=None, **kwargs):
        assert self._go_executable

        cmd = [
            self._go_executable,
            'build'
        ]
        if ldflags:
            cmd.extend(['-ldflags', ldflags])
        if install:
            cmd.append('-i')
        if force:
            cmd.append('-a')
        if output:
            cmd.extend(['-o', output])
        cmd.extend(packages)

        return self.m.step('go build', cmd)

    def run(self, files, *args, **kwargs):
        """Run an inline Go program as a step.
        Program is output to a temp file and run when this step executes.
        """
        assert self._go_executable

        cmd = [
            self._go_executable,
            'run'
        ] + files + list(args or [])

        return self.m.step('go run', cmd)

    def test(self, packages, **kwargs):
        assert self._go_executable

        cmd = [
            self._go_executable,
            'test'
        ] + packages

        return self.m.step('go test', cmd)
