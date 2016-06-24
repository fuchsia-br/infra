// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"fmt"
	"net/url"
	"os"

	"v.io/jiri/gerrit"
	"v.io/jiri/runutil"
)

var (
	logFilePath = "/tmp/mojo_presubmit_log.json"

	gerritURL   = "https://mojo-review.googlesource.com"
	gerritQuery = "status:open"
)

// createGerrit returns a handle to our gerrit instance.
func createGerrit() (*gerrit.Gerrit, error) {
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

// sendNewChangesForTesting queries Gerrit for new changes, where changes may be grouped into related
// sets that must be tested together (i.e. MultiPart changes), then sends them for testing.
func sendNewChangesForTesting() error {
	numberOfSentCLs := 0
	defer func() {
		fmt.Printf("Sent %d CLs for testing\n", numberOfSentCLs)
	}()

	// Grab handle to Gerrit.
	gerritHandle, err := createGerrit()
	if err != nil {
		return err
	}

	// Don't send any changes if the presubmit test job is currently failing.
	if err := lastPresubmitBuildError(); err != nil {
		return fmt.Errorf("Refusing to test new CLs because of existing failures\n%v", err)
	}

	// Read previously found CLs.
	fmt.Println("Using CL log: ", logFilePath)
	prevCLsMap, err := gerrit.ReadLog(logFilePath)
	if err != nil {
		return err
	}

	// Fetch pending CLs from Gerrit.
	curCLs, err := gerritHandle.Query(gerritQuery)
	if err != nil {
		return err
	}

	// Write the current list of pending CLs to a file.
	err = gerrit.WriteLog(logFilePath, curCLs)
	if err != nil {
		return err
	}

	// Compare the previous CLs to the current list to determine which new CLs we must
	// send for testing.
	newCLs, errList := gerrit.NewOpenCLs(prevCLsMap, curCLs)
	errMsg := ""
	for _, e := range errList {
		// NewOpenCLs may return errors detected when parsing MultiPart CL metadata.
		errMsg += fmt.Sprintf("NewOpenCLs error: %v\n", e)
	}
	if len(errMsg) > 0 {
		return fmt.Errorf(errMsg)
	}

	// Send the CLs for testing.
	sender := clsSender{
		clLists: newCLs,
		clsSent: 0,
		worker:  &JenkinsGerritCIWorker{},
	}
	if err := sender.sendCLsToPresubmitTest(); err != nil {
		return err
	}

	numberOfSentCLs = sender.clsSent
	return nil
}

// JenkinsGerritCIWorker implements a workflow for clsSender with jenkins as CI and gerrit for code review.
type JenkinsGerritCIWorker struct{}

func (jg *JenkinsGerritCIWorker) listTestsToRun() []string {
	return getTestsToRun()
}

func (jg *JenkinsGerritCIWorker) removeOutdatedBuilds(outdatedCLs map[clNumber]patchset) []error {
	return removeOutdatedBuilds(outdatedCLs)
}

func (jg *JenkinsGerritCIWorker) addPresubmitTestBuild(cls gerrit.CLList, testNames []string) error {
	return addPresubmitTestBuild(cls, testNames)
}

func (jg *JenkinsGerritCIWorker) postResults(message string, clRefs []string, verified bool) error {
	return postMessageToGerrit(message, clRefs, verified)
}

// postMessageToGerrit adds a message to the given ref on Gerrit, as a comment.  The verified
// argument determines whether we +1 or -1 the CL.
func postMessageToGerrit(message string, refs []string, verified bool) error {
	fmt.Printf("Posting message to Gerrit (%v::%v) %q\n", verified, refs, message)
	// TODO(lanechr): everything.
	return nil
}

func main() {
	if err := sendNewChangesForTesting(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
