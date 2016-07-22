#!/bin/bash

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

# This script is used by Jenkins to build the Fuchsia sysroot.

set -ex

if [[ -z "${JIRI_ROOT}" ]]; then
  echo "JIRI_ROOT must be set before running this script"
  exit 1
fi

readonly GERRIT_OPTS="cc=fuchsia-reviews@google.com"

readonly OUT_DIR="${JIRI_ROOT}/out"
readonly SDK_URL="gs://fuchsia-build/fuchsia/sysroot"

# Build the sysroots
export PATH="${JIRI_ROOT}/buildtools:${JIRI_ROOT}/buildtools/cmake/bin:${PATH}"
if [[ ! -d "${OUT_DIR}" ]]; then
  mkdir "${OUT_DIR}"
else
  ninja -C ${OUT_DIR} sysroot-distclean
fi
${JIRI_ROOT}/.jiri_root/bin/toyen -src "${JIRI_ROOT}" -out "${OUT_DIR}" "${JIRI_ROOT}/packages/root.bp"
ninja -C "${OUT_DIR}" -j1 sysroot

# Upload the sysroots
upload_sysroot() {
  local arch=$1
  local tarball="$(LC_ALL=POSIX cat $(find "${OUT_DIR}/sysroot/${arch}-fuchsia" -type f | sort) | shasum -a1  | awk '{print $1}')"
  tar -C ${OUT_DIR}/sysroot -jcvf "${tarball}" ${arch}-fuchsia
  if ! gsutil stat "${SDK_URL}/${arch}/${tarball}" &>/dev/null; then
    gsutil cp "${tarball}" "${SDK_URL}/${arch}/${tarball}"
    echo "${tarball}" > "${JIRI_ROOT}/buildtools/sysroot/${arch}-fuchsia.sha1"
  fi
  rm -f "${tarball}"
}

upload_sysroot "x86_64"
upload_sysroot "aarch64"

readonly MAGENTA_COMMIT="$(git -C "${JIRI_ROOT}/magenta" rev-parse --short HEAD)"

# Send a change
if ! git -C "${JIRI_ROOT}/buildtools" diff-files --quiet; then
  git -c "user.email=fuchsia.robot@gmail.com" -c "user.name=Fuchsia Robot" -C "${JIRI_ROOT}/buildtools" commit -m "Update Fuchsia sysroots" -m "Updated to Magenta commit ${MAGENTA_COMMIT}." -- sysroot/x86_64-fuchsia.sha1 sysroot/aarch64-fuchsia.sha1
  git -c "user.email=fuchsia.robot@gmail.com" -c "user.name=Fuchsia Robot" -C "${JIRI_ROOT}/buildtools" push origin HEAD:refs/for/master%${GERRIT_OPTS:-}
fi

# Cleanup
ninja -C ${OUT_DIR} sysroot-distclean
