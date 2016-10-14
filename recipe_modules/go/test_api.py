# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class GoTestApi(recipe_test_api.RecipeTestApi):

    def make_test_path(self):
        return str(self.m.path['slave_build'].join('go', 'go'))

    def make_test_version(self, v):
        if v:
            return v
        return 'go1.7'

    def example_install_go(self, version=None, retcode=None):
        return self.m.json.output({
            'path': self.make_test_path(),
            'version': self.make_test_version(version),
        }, retcode=retcode)
