// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package presubmit

// This file contains all the functions that contain Jenkins-specific logic.  Other
// files should be able to reference these functions without knowing what CI system
// is backing them.  No other files should even mention Jenkins.

import (
	"flag"
	"net/url"
	"strings"

	"v.io/jiri/gerrit"
	"v.io/jiri/jenkins"
)

var (
	jenkinsHost              = "http://localhost:8090/jenkins"
	jenkinsPresubmitTestName string
	jenkinsInstance          *jenkins.Jenkins
)

func init() {
	flag.StringVar(&jenkinsPresubmitTestName, "test", "presubmit-test", "The name of the presubmit test job")
}

// getJenkins returns a handle to the Jenkins instance in a non-thread-safe singleton fashion.
func getJenkins() (*jenkins.Jenkins, error) {
	if jenkinsInstance != nil {
		return jenkinsInstance, nil
	}
	var err error
	jenkinsInstance, err = jenkins.New(jenkinsHost)
	return jenkinsInstance, err
}

// CheckPresubmitBuildConfig returns an error if the presubmit build is not configured properly.
// It also returns an error if we fail to fetch the status of the build.
func CheckPresubmitBuildConfig() error {
	j, err := getJenkins()
	if err != nil {
		return err
	}

	_, err = j.LastCompletedBuildStatus(jenkinsPresubmitTestName, nil)
	if err != nil {
		return err
	}

	return nil
}

// RemoveOutdatedBuilds halts and removes presubmit builds that are no longer relevant.  This
// could happen because a contributor uploads a new patch set before the old one is finished testing.
func RemoveOutdatedBuilds(validCLs map[CLNumber]Patchset) (errs []error) {
	// TODO(lanechr): everything.
	return nil
}

// AddPresubmitTestBuild kicks off the presubmit test build on Jenkins.
func AddPresubmitTestBuild(cls gerrit.CLList) error {
	j, err := getJenkins()
	if err != nil {
		return err
	}

	refs := []string{}
	for _, cl := range cls {
		refs = append(refs, cl.Reference())
	}

	if err := j.AddBuildWithParameter(jenkinsPresubmitTestName, url.Values{
		"REFS":  {strings.Join(refs, " ")},
	}); err != nil {
		return err
	}

	return nil
}
