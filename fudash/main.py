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
        ('fuchsia/magenta-aarch64-linux-clang', 'magenta-aarch64-linux-clang'),
        ('fuchsia/magenta-aarch64-linux-gcc', 'magenta-aarch64-linux-gcc'),
        ('fuchsia/magenta-x86_64-linux-clang', 'magenta-x86_64-linux-clang'),
        ('fuchsia/magenta-x86_64-linux-gcc', 'magenta-x86_64-linux-gcc'),
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

    def __init__(self):
        HTMLParser.__init__(self)
        self.parsing_invocations = False
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
                if k == 'class' and v == 'danger':
                    self.result = BuildResult.Fail
                    self.stop_parsing = True
                if k == 'class' and v == 'success':
                    self.result = BuildResult.Pass
                    self.stop_parsing = True

class MainPage(webapp2.RequestHandler):
    """The main handler."""

    @staticmethod
    def getBuildResult(target):
        try:
            resp = urlfetch.fetch(BASE_URL + target, deadline=5)
            if resp.status_code != 200:
                return BuildResult.ServerError
            parser = LuciResultParser()
            parser.feed(resp.content)
            parser.close()
            return parser.result
        except:
            return BuildResult.ServerError

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
                result = {
                    'name': display_name,
                    'result': MainPage.getBuildResult(url_suffix),
                    'href': BASE_URL + url_suffix,
                }
                build_jobs.append(result)
            target = {
                'project': t,
                'build_jobs': build_jobs
            }
            template_values['targets'].append(target)

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


app = webapp2.WSGIApplication([
        ('/', MainPage),
], debug=True)
