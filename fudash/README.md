# Hacky interim dashboard

This is a hacky dashboard that serves the purpose of collecting all the
LUCI build results into one location.  It works by scraping the pages served
on luci-scheduler.appspot.com.  It does that because that's the only
unauthenticated place where the build results are surfaced.

# Making changes / testing / deploying

This is a normal App Engine app.  As such, you should use typical App Engine
workflow -- [documentation here](https://cloud.google.com/appengine/docs/python/).

## Testing local changes

```
dev_appserver.py ./app.yaml
```

## Deploying new versions

```
gcloud config set project $project_name
gcloud app deploy app.yaml
```
