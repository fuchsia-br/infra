#!/usr/bin/env bash

# Copyright 2016 The Fuchsia Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

# Make sure $JIRI_ROOT isn't blank because we're going to use it later to construct paths.
if [[ -z "${JIRI_ROOT}" ]]; then
  echo "JIRI_ROOT must be set!"
  exit 99
fi

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 [build-name-to-kick-off] [comma-separated list of repos to watch]"
  echo "Example: $0 ignore-fuchsia-magenta-build magenta,infra"
  exit 1
fi

set -x
readonly BUILD_NAME="$1"
readonly REPO_LIST="$2"

cd "${JIRI_ROOT}"
export GOPATH="${JIRI_ROOT}/infra/go:${JIRI_ROOT}/go"
go build presubmit/submit-watch
./submit-watch -logfile "/tmp/${BUILD_NAME}.watchlog.json" -project "${REPO_LIST}" -build "${BUILD_NAME}"
