// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"fmt"
	"os"

	"presubmit"
	"v.io/jiri/gerrit"
)

var (
	logFilePath = "/tmp/mojo_presubmit_log.json"
)

// sendNewChangesForTesting queries gerrit for new changes, where changes may be grouped into related
// sets that must be tested together (i.e. MultiPart changes.), then sends them for testing.
func sendNewChangesForTesting() error {
	numberOfSentCLs := 0
	defer func() {
		fmt.Printf("Sent %d CLs for testing\n", numberOfSentCLs)
	}()

	// Grab handle to Gerrit.
	gerritHandle, err := presubmit.CreateGerrit()
	if err != nil {
		return err
	}

	// Don't send any changes if the presubmit test job is currently failing.
	if err := presubmit.LastPresubmitBuildError(); err != nil {
		return fmt.Errorf("Refusing to test new CLs because of existing failures\n%v", err)
	}

	// Read previously found CLs.
	fmt.Println("Using CL log: ", logFilePath)
	prevCLsMap, err := gerrit.ReadLog(logFilePath)
	if err != nil {
		return err
	}

	// Fetch pending CLs from Gerrit.
	curCLs, err := gerritHandle.Query(presubmit.GerritQuery)
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
	sender := presubmit.CLsSender{
		CLLists: newCLs,
		Worker:  &JenkinsGerritCIWorker{},
	}
	if err := sender.SendCLsToPresubmitTest(); err != nil {
		return err
	}

	numberOfSentCLs = sender.CLsSent
	return nil
}

// JenkinsGerritCIWorker implements a workflow for clsSender with jenkins as CI and gerrit for code review.
type JenkinsGerritCIWorker struct{}

func (jg *JenkinsGerritCIWorker) ListTestsToRun() []string {
	return presubmit.GetTestsToRun()
}

func (jg *JenkinsGerritCIWorker) RemoveOutdatedBuilds(outdatedCLs map[presubmit.CLNumber]presubmit.Patchset) []error {
	return presubmit.RemoveOutdatedBuilds(outdatedCLs)
}

func (jg *JenkinsGerritCIWorker) AddPresubmitTestBuild(cls gerrit.CLList, testNames []string) error {
	return presubmit.AddPresubmitTestBuild(cls, testNames)
}

func (jg *JenkinsGerritCIWorker) PostResults(message string, clRefs []string, verified bool) error {
	return presubmit.PostMessageToGerrit(message, clRefs, verified)
}

func main() {
	if err := sendNewChangesForTesting(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
