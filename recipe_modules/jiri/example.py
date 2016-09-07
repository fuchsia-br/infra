# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'jiri',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api):
    # First, ensure we have jiri.
    api.jiri.set_config(api.properties.get('config'))
    api.jiri.ensure_jiri()
    assert api.jiri.jiri

    # Setup a new jiri root.
    api.jiri.init('dir')

    # Import the manifest.
    api.jiri.import_manifest('minimal', 'https://fuchsia.googlesource.com',
                             overwrite=True)

    # Download all projects.
    api.jiri.update(gc=True, manifest='minimal')

    # Patch in an existing change.
    api.jiri.patch('refs/changes/1/2/3',
                   host='https://fuchsia-review.googlesource.com',
                   delete=True, force=True)

    # Clean up after ourselves.
    api.jiri.clean_project(branches=True)


def GenTests(api):
    yield api.test('basic')
    for config in ('jiri', 'magenta', 'fuchsia'):
      yield (
          api.test('basic_%s' % config) +
          api.properties(config=config)
      )
