#!/usr/bin/env python

# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

import os
from HTMLParser import HTMLParser

from google.appengine.api import urlfetch

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

BASE_URL = 'https://luci-scheduler.appspot.com/jobs/'

TARGETS = [
    'fuchsia/linux-x86-64',
    'fuchsia/linux-arm64',
    'magenta/arm32-linux-gcc',
    'magenta/arm64-linux-gcc',
    'magenta/x86-64-linux-gcc',
    'jiri/linux-x86-64',
    'jiri/mac-x86-64',
]

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
        resp = urlfetch.fetch(BASE_URL + target)
        if resp.status_code != 200:
            return BuildResult.ServerError
        parser = LuciResultParser()
        parser.feed(resp.content)
        parser.close()
        return parser.result

    def get(self):
        template_values = {
            'targets': []
        }
        for t in TARGETS:
            result = {
                'name': t,
                'result': MainPage.getBuildResult(t),
                'href': BASE_URL + t,
            }
            template_values['targets'].append(result)

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


app = webapp2.WSGIApplication([
        ('/', MainPage),
], debug=True)
