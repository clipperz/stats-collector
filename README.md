Clipperz stats collector
========================

Overview
--------

This is a very simple tool to collect stats of Clipperz application performances.
There is a "client" script (`collectData.py`) that will perform a full authentication on the live Clipperz server and collect some data and timing info in the process; the collected data will than be sent to the collector script running on `collector.stats.clipperz.is`.
The current version of the "server" script (`collector.py`) will repack the data in a Splunk friendly format, and forward it to SplunkStorm [1] where all the data are actually collected.

[1]: https://www.splunkstorm.com


Running the client
------------------

The client is meant to be executed across the world, in order to understand better how the application behaves globally.


### AUTH_KEY

In order to avoid fluding Splunk with crap data, we are asking anyone willing to help us in monitoring the application to ask for an authentication key.

### SCRIPT

#### CURL
export AUTH_KEY="__FAKE__"; export URL="https://clipperz.is"; export USERNAME="joe"; export PASSPHRASE="clipperz"; python <(curl -s https://raw.github.com/clipperz/stats-collector/master/collectData.py)

#### WGET
export AUTH_KEY="__FAKE__"; export URL="https://clipperz.is"; export USERNAME="joe"; export PASSPHRASE="clipperz"; python <(wget -qO- https://raw.github.com/clipperz/stats-collector/master/collectData.py)