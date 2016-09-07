# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class PathsApi(recipe_api.RecipeApi):
    def initialize(self):
        self.m.path.set_config(
            self.m.properties.get('path_config', 'swarmbucket'))
