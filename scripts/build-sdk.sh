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

readonly OUT_DIR="${JIRI_ROOT}/out"
readonly SYSROOT_BUCKET="gs://fuchsia-build/fuchsia/sysroot"
readonly MAGENTA_BUCKET="gs://fuchsia-build/magenta"

readonly MAGENTA_HASH="$(git -C "${JIRI_ROOT}/magenta" rev-parse --short HEAD)"
readonly MAGENTA_COMMIT="$(git -C "${JIRI_ROOT}/magenta" rev-parse HEAD)"

readonly GERRIT_OPTS="topic=magenta/${MAGENTA_HASH},cc=fuchsia-reviews@google.com"

# Build the sysroots
export PATH="${JIRI_ROOT}/buildtools:${JIRI_ROOT}/buildtools/cmake/bin:${PATH}"
if [[ ! -d "${OUT_DIR}" ]]; then
  mkdir "${OUT_DIR}"
else
  ninja -C ${OUT_DIR} sysroot-distclean
fi
${JIRI_ROOT}/.jiri_root/bin/toyen -src "${JIRI_ROOT}" -out "${OUT_DIR}" "${JIRI_ROOT}/packages/root.bp"
ninja -C "${OUT_DIR}" -j1 sysroot

readonly MAGENTA_BINARIES=("magenta.bin" "magenta.elf")
readonly MAGENTA_TOOLS=("bootserver" "loglistener" "mkbootfs" "netruncmd")

# Upload Magenta
upload_magenta() {
  local arch=$1
  for file in ${MAGENTA_BINARIES[@]}; do
    gsutil cp "${OUT_DIR}/build-magenta-${arch}/${file}" "${MAGENTA_BUCKET}/${arch}/${file}/${MAGENTA_COMMIT}"
    echo "${MAGENTA_COMMIT}" > "${JIRI_ROOT}/packages/prebuilt/versions/magenta/${arch}/${file}"
  done
}

upload_tools() {
  local arch=$1
  for file in ${MAGENTA_TOOLS[@]}; do
    gsutil cp "${OUT_DIR}/build-magenta-${arch}/tools/${file}" "${MAGENTA_BUCKET}/tools/${file}/${MAGENTA_COMMIT}"
    echo "${MAGENTA_COMMIT}" > "${JIRI_ROOT}/packages/prebuilt/versions/magenta/tools/${file}"
  done
}

upload_magenta "qemu-arm64"
upload_magenta "pc-x86-64"
upload_tools "pc-x86-64"

# Send a change
if ! git -C "${JIRI_ROOT}/packages" diff-files --quiet; then
  git -c "user.email=fuchsia.robot@gmail.com" -c "user.name=Fuchsia Robot" -C "${JIRI_ROOT}/packages" commit -m "Update Magenta prebuilts" -m "Updated to Magenta commit ${MAGENTA_HASH}." -- packages/prebuilt/versions/magenta/*
  git -c "user.email=fuchsia.robot@gmail.com" -c "user.name=Fuchsia Robot" -C "${JIRI_ROOT}/packages" push origin HEAD:refs/for/master%${GERRIT_OPTS:-}
fi

# Upload the sysroots
upload_sysroot() {
  local arch=$1
  local tarball="$(LC_ALL=POSIX cat $(find "${OUT_DIR}/sysroot/${arch}-fuchsia" -type f | sort) | shasum -a1  | awk '{print $1}')"
  tar -C ${OUT_DIR}/sysroot -jcvf "${tarball}" ${arch}-fuchsia
  if ! gsutil stat "${SYSROOT_BUCKET}/${arch}/${tarball}" &>/dev/null; then
    gsutil cp "${tarball}" "${SYSROOT_BUCKET}/${arch}/${tarball}"
    echo "${tarball}" > "${JIRI_ROOT}/buildtools/sysroot/${arch}-fuchsia.sha1"
  fi
  rm -f "${tarball}"
}

upload_sysroot "x86_64"
upload_sysroot "aarch64"

# Send a change
if ! git -C "${JIRI_ROOT}/buildtools" diff-files --quiet; then
  git -c "user.email=fuchsia.robot@gmail.com" -c "user.name=Fuchsia Robot" -C "${JIRI_ROOT}/buildtools" commit -m "Update Fuchsia sysroots" -m "Updated to Magenta commit ${MAGENTA_HASH}." -- sysroot/x86_64-fuchsia.sha1 sysroot/aarch64-fuchsia.sha1
  git -c "user.email=fuchsia.robot@gmail.com" -c "user.name=Fuchsia Robot" -C "${JIRI_ROOT}/buildtools" push origin HEAD:refs/for/master%${GERRIT_OPTS:-}
fi

# Cleanup
ninja -C ${OUT_DIR} sysroot-distclean
