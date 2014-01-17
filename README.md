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

## Environment
In order to be able to execute the collector script, you need to have the 'requests' library installed.
On a plain Ubuntu Server 12.04 LTE these are the steps required to set everything up:

    $ sudo apt-get install -y python-pip
    $ sudo pip install requests

### AUTH_KEY

In order to avoid flooding Splunk with crap data, we are asking anyone willing to help us in monitoring the application to ask for an authentication key.

### SCRIPT

#### CURL
export AUTH_KEY="__SAMPLE_KEY__"; python <(curl -s https://raw.github.com/clipperz/stats-collector/master/collectData.py)

#### WGET
export AUTH_KEY="__SAMPLE_KEY__"; python <(wget -qO- https://raw.github.com/clipperz/stats-collector/master/collectData.py)

### Cron
In order to collect data regularly, it is possible to schedule the script with `cron`; an entry like this should do the job:

*/15 * * * * export AUTH_KEY="__SAMPLE_KEY__"; python <(curl -s https://raw.github.com/clipperz/stats-collector/master/collectData.py) > /dev/null 2>&1
