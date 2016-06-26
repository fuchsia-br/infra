// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"flag"
	"fmt"
	"os"
	"strconv"
	"strings"

	"presubmit"
	"v.io/jiri"
	"v.io/jiri/gerrit"
	"v.io/jiri/gitutil"
	"v.io/jiri/project"
	"v.io/jiri/runutil"
	"v.io/x/lib/cmdline"
)

var (
	refsToTest string
)

func init() {
	flag.StringVar(&refsToTest, "cl", "", "comma-separated list of change/patchset. Example: 1153/2,1150/1")
}

// splitRef parses the string arguments given to the -cl flag.
func splitRef(ref string) (changelist int, patchset int, e error) {
	parts := strings.Split(ref, "/")
	if len(parts) != 2 {
		// Allow for ref strings in the form of a gerrit reference.
		if strings.HasPrefix(ref, "refs/changes/") && len(parts) == 5 {
			parts = parts[3:]
		} else {
			return 0, 0, fmt.Errorf(
				"malformed cl string: %q; examples of supported forms are: 'refs/changes/53/1153/2', or '1153/2'\n", ref)
		}
	}
	changelist, e = strconv.Atoi(parts[0])
	if e != nil {
		return 0, 0, e
	}
	patchset, e = strconv.Atoi(parts[1])
	if e != nil {
		return 0, 0, e
	}
	e = nil
	return
}

// gerritProjectToJiriProject takes the name of a project in gerrit/gob and returns the corresponding
// project name as expressed in our jiri manifests.  v23 handles this through the policy that the
// names must be equal, but we don't have a plan for this yet.
func gerritProjectToJiriProject(gerritProject string) string {
	switch gerritProject {
	case "mojo-manifest":
		return "manifest"
	}
	return gerritProject
}

// readJiriManifest reads the jiri manifest found in JIRI_ROOT.
func readJiriManifest() (project.Projects, error) {
	jirix, err := jiri.NewX(cmdline.EnvFromOS())
	if err != nil {
		return nil, err
	}
	projects, _, err := project.LoadManifest(jirix)
	if err != nil {
		return nil, err
	}
	return projects, nil
}

// patchProject changes directory into the project directory, checks out the given
// change, then cds back to the original directory.
func patchProject(jiriProject project.Project, cl gerrit.Change) error {
	cwd, err := os.Getwd()
	if err != nil {
		return err
	}

	defer os.Chdir(cwd)
	err = os.Chdir(jiriProject.Path)
	if err != nil {
		return err
	}

	seq := runutil.NewSequence(nil, os.Stdin, os.Stdout, os.Stderr, false, false)
	git := gitutil.New(seq)

	err = git.CreateAndCheckoutBranch("underscore-presubmit")
	if err != nil {
		return err
	}

	// If the pull fails, it's likely because of a merge conflict.
	err = git.Pull(jiriProject.Remote, cl.Reference())
	if err != nil {
		return err
	}

	return nil
}

// quitOnError is a convenience function for printing an error and exiting the program.
func quitOnError(e error) {
	if e != nil {
		fmt.Fprintf(os.Stderr, "%v\n", e)
		os.Exit(1)
	}
}

func main() {
	flag.Parse()

	g, err := presubmit.CreateGerrit()
	quitOnError(err)

	// Construct the list of changes we're going to test.
	cls := []gerrit.Change{}
	for _, ref := range strings.Split(refsToTest, ",") {
		clNumber, patchset, err := splitRef(ref)
		quitOnError(err)

		cl, err := g.GetChange(clNumber)
		quitOnError(err)

		foundCl, foundPs, err := gerrit.ParseRefString(cl.Reference())
		quitOnError(err)

		// Abandon the test if we were given outdated patchsets.
		if foundPs != patchset {
			quitOnError(fmt.Errorf("%q is outdated; there's a newer patchset (%d/%d)\n",
				ref, foundCl, foundPs))
		}

		fmt.Printf("Found patch: %s, %s\n", cl.Project, cl.Reference())

		cls = append(cls, *cl)
	}

	// Read the project manifest.  We need this information to know which directories and remotes
	// map to the project names that come back from gerrit.
	projects, err := readJiriManifest()
	quitOnError(err)

	// Patch the projects that changed.
	for _, cl := range cls {
		localProject, err := projects.FindUnique(gerritProjectToJiriProject(cl.Project))
		quitOnError(err)

		err = patchProject(localProject, cl)
		quitOnError(err)
	}
}
