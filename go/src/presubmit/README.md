# Presubmit
This directory contains code for fetching new changelists from Gerrit and
testing them against some CI system (currently Jenkins.)

# Building
Build these tools using `go build`.

There is no integration with an overall build system or checkout system (yet.)
For now, you will have to meet the dependency on `v.io/jiri` manually and set
your `GOPATH` accordingly.

We expect this tool to be built and run automatically on the CI system.

# Build example
Given the following directory structure:

```
/work/infra/go/src/presubmit/...
/work/v23/release/go/src/v.io/...
```

These commands would work, and will generate tools in your current directory.

```
$ export GOPATH=/work/infra/go/:/work/v23/release/go
$ go build presubmit/query
$ go build presubmit/patch
```

# Running
The presubmit logic is organized into two different tools: `query` and `patch`.

`query` checks Gerrit for new CLs and sends them to CI for testing.
`patch` is used by CI to patch the given CLs into its code tree.

## query
Running `query` directly with no arguments will cause it to inspect
`mojo.googlesource.com` for new CLs and send those refs to a Jenkins instance on
localhost for testing.

There's a fair amount of configuration expected on the Jenkins instance; in
particular that there exists a matrix configuration build named
`mojo-presubmit-test` that expects parameters in the form of `REFS` and `TESTS`
(the CLs to apply and the tests to run, respectively.)

The mojo assumption is temporary, and this tool will soon be parameterized to
work for all of our projects.

## patch
Internally, the CI jobs will use `presubmit/patch` to take the CLs given and
patch its code tree before building and running tests.
