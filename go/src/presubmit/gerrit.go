// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package presubmit

import (
	"flag"
	"fmt"
	"net/url"
	"os"
	"v.io/jiri/gerrit"
	"v.io/jiri/runutil"
)

var (
	gerritURL   string
	GerritQuery = "status:open"
)

func init() {
	flag.StringVar(&gerritURL, "gerrit", "", "The Gerrit endpoint, e.g. https://foo-review.googlesource.com")
}

// CreateGerrit returns a handle to our gerrit instance.
func CreateGerrit() (*gerrit.Gerrit, error) {
	if len(gerritURL) == 0 {
		return nil, fmt.Errorf("No gerrit host to query; use the -gerrit flag")
	}

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
	g, err := CreateGerrit()
	if err != nil {
		return err
	}

	// For all the given refs, post a review with the given message.
	for _, ref := range refs {
		if err = g.PostReview(ref, message, nil); err != nil {
			return err
		}
	}

	// TODO(lanechr): Set the Verified label.  Can't do this until the Gerrit repos are
	// configured to expect it.  Need to look at v23 repos as an example.

	return nil
}
