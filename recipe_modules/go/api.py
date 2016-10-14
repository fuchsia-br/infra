# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

import textwrap


class GoApi(recipe_api.RecipeApi):
    """GoApi provides support for Go."""

    def __init__(self, *args, **kwargs):
        super(GoApi, self).__init__(*args, **kwargs)
        self._go_dir = None
        self._go_version = None

    def __call__(self, *args, **kwargs):
        """Return a Go command step."""
        assert self._go_dir

        name = kwargs.pop('name', 'go ' + args[0])
        env = kwargs.setdefault('env', {})
        go_cmd = [self.go_executable]
        env.setdefault('GOROOT', self._go_dir)

        return self.m.step(name, go_cmd + list(args or []), **kwargs)

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
        self._go_dir = step.json.output['path']
        step.presentation.step_text = (
                'Go version: %s' % step.json.output['version'])
        return step

    @property
    def go_executable(self):
        return self.m.path.join(self._go_dir, 'bin', 'go')

    def inline(self, program, add_go_log=True, **kwargs):
        """Run an inline Go program as a step.
        Program is output to a temp file and run when this step executes.
        """
        program = textwrap.dedent(program)

        try:
            self('run', self.m.raw_io.input(program, '.go'), **kwargs)
        finally:
            result = self.m.step.active_result
            if result and add_go_log:
                result.presentation.logs['go.inline'] = program.splitlines()

        return result
