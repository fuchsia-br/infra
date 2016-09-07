# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import ConfigList, Dict, Single, Static, Set, List


def BaseConfig(**kwargs):
    return ConfigGroup(
        manifests = ConfigList(
            lambda: ConfigGroup(
                manifest = Single(basestring, required=True),
                remote = Single(str, required=True),
            )
        )
    )


config_ctx = config_item_context(BaseConfig)


@config_ctx()
def jiri(c):
    m = c.manifests.add()
    m.manifest = 'jiri'
    m.remote = 'https://fuchsia.googlesource.com/manifest'


@config_ctx()
def magenta(c):
    m = c.manifests.add()
    m.manifest = 'magenta'
    m.remote = 'https://fuchsia.googlesource.com/manifest'


@config_ctx()
def fuchsia(c):
    m = c.manifests.add()
    m.manifest = 'fuchsia'
    m.remote = 'https://fuchsia.googlesource.com/manifest'
