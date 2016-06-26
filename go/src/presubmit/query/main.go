// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"flag"
	"fmt"
	"os"
	"strings"

	"presubmit"
	"v.io/jiri/gerrit"
)

var (
	repoList    string
	logFilePath string
	forceSend   bool
)

func init() {
	flag.StringVar(&repoList, "repo", "", "Comma separated list of repos to query")
	flag.StringVar(&logFilePath, "logfile", "/tmp/fuchsia-presubmit-log.json", "Full path of log file to use")
	flag.BoolVar(&forceSend, "f", false, "Send all changes, even if they've already been sent")
}

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
	var prevCLsMap gerrit.CLRefMap
	if !forceSend {
		fmt.Println("Using CL log:", logFilePath)
		prevCLsMap, err = gerrit.ReadLog(logFilePath)
		if err != nil {
			return err
		}
	} else {
		fmt.Println("Sending all pending changes")
	}

	// Fetch pending CLs from Gerrit.
	pendingCLs, err := gerritHandle.Query(presubmit.GerritQuery)
	if err != nil {
		return err
	}

	// Filter the list of CLs by repo.
	var filteredCLs gerrit.CLList
	if len(repoList) != 0 {
		repoFilterList := map[string]bool{}
		for _, repo := range strings.Split(repoList, ",") {
			repoFilterList[repo] = true
		}

		for _, cl := range pendingCLs {
			if repoFilterList[cl.Project] {
				filteredCLs = append(filteredCLs, cl)
			}
		}
	} else {
		filteredCLs = pendingCLs
	}

	// Write the current list of pending CLs to a file.
	err = gerrit.WriteLog(logFilePath, filteredCLs)
	if err != nil {
		return err
	}

	// Compare the previous CLs to the current list to determine which new CLs we must
	// send for testing.
	newCLs, errList := gerrit.NewOpenCLs(prevCLsMap, filteredCLs)
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
	flag.Parse()

	if err := sendNewChangesForTesting(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
