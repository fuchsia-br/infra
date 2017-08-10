#!/usr/bin/env python

# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

import os
import time
from HTMLParser import HTMLParser

from google.appengine.api import urlfetch

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

BASE_URL = 'https://luci-scheduler.appspot.com/jobs/'
SNAPSHOT_URL = 'https://storage.googleapis.com/fuchsia/jiri/snapshots'

TARGETS = {
    'fuchsia': [
        ('fuchsia/fuchsia-aarch64-linux-debug', 'fuchsia-aarch64-linux-debug'),
        ('fuchsia/fuchsia-aarch64-linux-release', 'fuchsia-aarch64-linux-release'),
        ('fuchsia/fuchsia-x86_64-linux-debug', 'fuchsia-x86_64-linux-debug'),
        ('fuchsia/fuchsia-x86_64-linux-release', 'fuchsia-x86_64-linux-release'),
    ],
    'fuchsia-drivers': [
        ('fuchsia/drivers-aarch64-linux-debug', 'drivers-aarch64-linux-debug'),
        ('fuchsia/drivers-aarch64-linux-release', 'drivers-aarch64-linux-release'),
        ('fuchsia/drivers-x86_64-linux-debug', 'drivers-x86_64-linux-debug'),
        ('fuchsia/drivers-x86_64-linux-release', 'drivers-x86_64-linux-release'),
    ],
    'magenta': [
        ('fuchsia/magenta-qemu-arm64-clang', 'magenta-qemu-arm64-clang'),
        ('fuchsia/magenta-qemu-arm64-gcc', 'magenta-qemu-arm64-gcc'),
        ('fuchsia/magenta-pc-x86-64-clang', 'magenta-pc-x86-64-clang'),
        ('fuchsia/magenta-pc-x86-64-gcc', 'magenta-pc-x86-64-gcc'),
    ],
    'jiri': [
        ('fuchsia/jiri-x86_64-linux', 'jiri-x86_64-linux'),
        ('fuchsia/jiri-x86_64-mac', 'jiri-x86_64-mac'),
    ]
}


class BuildResult:
    """This is an enum of sorts, except the values match css class names."""
    Pass = "pass"
    Fail = "fail"
    ServerError = "server_error"
    ParserError = "parser_error"


class LuciResultParser(HTMLParser):
    """Parses the HTML of the LUCI scheduler page to get the build results."""

    def __init__(self, success_only=False):
        HTMLParser.__init__(self)
        self.success_only = success_only
        self.parsing_invocations = False
        self.parsing_row = False
        self.stop_parsing = False
        self.result = BuildResult.ParserError

    def handle_starttag(self, tag, attrs):
        if self.stop_parsing: return
        if tag == 'table':
            for k, v in attrs:
                if k == 'id' and v == 'invocations-table':
                    self.parsing_invocations = True
        elif tag == 'tr' and self.parsing_invocations:
            for k, v in attrs:
                if k == 'class' and v == 'danger' and not self.success_only:
                    self.result = BuildResult.Fail
                    self.parsing_invocations = False
                    self.parsing_row = True
                if k == 'class' and v == 'success':
                    self.result = BuildResult.Pass
                    self.parsing_invocations = False
                    self.parsing_row = True
        elif tag == 'a' and self.parsing_row:
            for k, v in attrs:
                if k == 'href':
                    self.link = v
                if k == 'class' and 'label' in v:
                    self.stop_parsing = True


def getBuildResult(target, success_only=False):
    try:
        resp = urlfetch.fetch(BASE_URL + target, deadline=5)
        if resp.status_code != 200:
            return BuildResult.ServerError, '#'
        parser = LuciResultParser(success_only)
        parser.feed(resp.content)
        parser.close()
        return parser.result, parser.link
    except:
        return BuildResult.ServerError, '#'


class MiloResultParser(HTMLParser):
    """Parses the HTML of the Milo steps to get the snapshot link."""

    def __init__(self):
        HTMLParser.__init__(self)
        self.stop_parsing = False
        self.link = None

    def handle_starttag(self, tag, attrs):
        if self.stop_parsing: return
        if tag == 'a':
            for k, v in attrs:
                if k == 'href' and v.startswith(SNAPSHOT_URL):
                    self.link = v
                    self.stop_parsing= True


def getSnapshot(href):
    try:
        resp = urlfetch.fetch(href, deadline=5)
        if resp.status_code != 200:
            return BuildResult.ServerError
        parser = MiloResultParser()
        parser.feed(resp.content)
        parser.close()
        return parser.link
    except:
        return BuildResult.ServerError


class MainPage(webapp2.RequestHandler):
    """The main handler."""

    def get(self):
        template_values = {
            'clock': time.strftime("%H:%M UTC", time.gmtime()),
            'targets': [],
        }
        for t in sorted(TARGETS):
            build_jobs = []
            for job in TARGETS[t]:
                url_suffix = job[0]
                display_name = job[1]
                result, link = getBuildResult(url_suffix)
                result = {
                    'name': display_name,
                    'result': result,
                    'href': link,
                }
                build_jobs.append(result)
            target = {
                'project': t,
                'build_jobs': build_jobs
            }
            template_values['targets'].append(target)

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


class SnapshotPage(webapp2.RequestHandler):
    """The snapshot handler."""

    def get(self, target):
        snapshot_found = False
        for t in sorted(TARGETS):
            for j in TARGETS[t]:
                if target == j[1]:
                    result, link = getBuildResult(j[0], True)
                    self.redirect(getSnapshot(link))
                    snapshot_found = True
        if not snapshot_found:
            self.abort(404)


app = webapp2.WSGIApplication([
        ('/', MainPage),
        (r'/lkgs/([a-z0-9-_]+)', SnapshotPage),
], debug=True)
