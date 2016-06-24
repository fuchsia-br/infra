// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package presubmit

import (
	"fmt"
	"os"
	"net/url"
	"v.io/jiri/gerrit"
	"v.io/jiri/runutil"
)

var (
	gerritURL   = "https://mojo-review.googlesource.com"
	GerritQuery = "status:open"
)

// CreateGerrit returns a handle to our gerrit instance.
func CreateGerrit() (*gerrit.Gerrit, error) {
	// v.io/jiri/gerrit executes its commands through a v.io/jiri/runutil.Sequence object.
	//
	// runutil.Sequence contains environment variables, provides a place to override
	// std{in,out,err}, and has options for color and verbosity.  It also provides syntactic
	// sugar for executing multiple shell commands in a sequence (hence the name.)
	seq := runutil.NewSequence(nil, os.Stdin, os.Stdout, os.Stderr, false, false)

	u, err := url.Parse(gerritURL)
	if err != nil {
		return nil, err
	}

	return gerrit.New(seq, u), nil
}

// Post the given message to the given list of refs on Gerrit.
func PostMessageToGerrit(message string, refs []string, success bool) error {
	fmt.Printf("Posting message to Gerrit (%v::%v) %q\n", success, refs, message)
	// TODO(lanechr): everything.
	return nil
}
