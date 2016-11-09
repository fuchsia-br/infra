# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class JiriTestApi(recipe_test_api.RecipeTestApi):

    def example_describe(self, projects):
        assert projects is not None
        return self.m.json.output([
            {
                "name": project,
                "path": "/path/to/repo",
                "remote": "https://fuchsia.googlesource.com/repo",
                "revision": "c22471f4e3f842ae18dd9adec82ed9eb78ed1127",
                "current_branch": "",
                "branches": [
                    "(HEAD detached at c22471f)",
                    "master"
                ]
            }
            for project in projects
        ])
