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

# This script is used to create new bot instances on Google Compute Engine.

declare ZONE="${ZONE:-us-central1-c}"
declare MACHINE_TYPE="${MACHINE_TYPE:-n1-standard-4}"
declare DISK_SIZE="${DISK_SIZE:-50}"
declare DISK_TYPE="${DISK_TYPE:-pd-standard}"

set -eo pipefail; [[ "$TRACE" ]] && set -x

usage() {
  printf >&2 '%s: [-r release] [-m mirror] [-s] [-E] [-e] [-c] [-d] [-t timezone] [-p packages] [-b]\n' "$0" && exit 1
}

create() {
  local zone="$1" machine_type="$2" disk_size="$3" disk_type="$4"
  local botid="$(cat /dev/urandom | env LC_CTYPE=C tr -dc 'a-z0-9' | fold -w 4 | head -n 1)"

  gcloud compute instances create "fuchsia-bot-${botid}" \
    --zone "${zone}" \
    --machine-type "${machine_type}" \
    --network "default" \
    --metadata-from-file "startup-script=gce-startup-script.sh" \
    --maintenance-policy "MIGRATE" \
    --scopes default="https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring.write","https://www.googleapis.com/auth/pubsub","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/userinfo.email" \
    --tags "use-swarming-auth" \
    --image "/ubuntu-os-cloud/ubuntu-1404-trusty-v20160809a" \
    --boot-disk-size "${disk_size}" \
    --boot-disk-type "${disk_type}" \
    --boot-disk-device-name "fuchsia-bot-${botid}"
}

while getopts "hz:m:s:t:" opt; do
  case $opt in
    z) ZONE="$OPTARG";;
    m) MACHINE_TYPE="$OPTARG";;
    s) DISK_SIZE="$OPTARG";;
    t) DISK_TYPE="$OPTARG";;
    *) usage;;
  esac
done

create "${ZONE}" "${MACHINE_TYPE}" "${DISK_SIZE}" "${DISK_TYPE}"
