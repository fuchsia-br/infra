#!/bin/bash

# [START startup]
set -v

# Install logging monitor
# [START logging]
curl -s "https://storage.googleapis.com/signals-agents/logging/google-fluentd-install.sh" | bash
service google-fluentd restart &
# [END logging]

# Install dependencies from apt
apt-get update
apt-get install -yq git build-essential python

# Create a swarming user
useradd -m -d /home/swarming swarming
grep -q -F 'swarming ALL=NOPASSWD: /sbin/shutdown -r now' /etc/sudoers || echo 'swarming ALL=NOPASSWD: /sbin/shutdown -r now' >>/etc/sudoers

# Setup swarming service
mkdir -p /b/swarm_slave
python - <<END
import requests
r = requests.get('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token', headers={'Metadata-Flavor': 'Google'})
r = requests.get('https://chromium-swarm-dev.appspot.com/bot_code', headers={'Authorization': 'Bearer %(access_token)s' % r.json()}, stream=True)
with open('/b/swarm_slave/swarming_bot.zip', 'wb') as fd:
  for chunk in r.iter_content(chunk_size=4096):
    fd.write(chunk)
END
chown -R swarming:swarming /b/swarm_slave

cat >/etc/init/swarming.conf <<EOF
description "Swarming bot"

start on filesystem or runlevel [2345]
stop on shutdown

respawn
respawn limit 0 10

setuid swarming

exec /usr/bin/env python /b/swarm_slave/swarming_bot.zip start_bot
EOF

service swarming restart &

# [END startup]
