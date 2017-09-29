#!/usr/bin/env python

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

import json
import requests
import sys
import string

def main():
    r = requests.get('https://fuchsia-review.googlesource.com/projects/')
    if r.status_code != 200:
        print 'Failed to download project list: %d' % r.status_code
        return 1
    projects = json.loads(r.text[5:])
    with open('list-of-repos.txt') as current_list:
        listed_projects = map(string.strip, current_list.readlines())
    meta_projects = ['All-Projects', 'All-Users', 'Read-Only', 'gerrit/verified-projects']
    project_diff = set(projects.keys()) - set(meta_projects) - set(listed_projects)
    if len(project_diff) != 0:
        print 'The following projects are not in list-of-repos.txt:'
        project_diff_sorted = list(project_diff)
        project_diff_sorted.sort()
        for p in project_diff_sorted:
            print p
    return 0

if __name__ == '__main__':
    sys.exit(main())
