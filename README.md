# InfoScroller

Python project to display different info on an LDP-8008 matrix display. Currently displays information on drive times and now playing on local chromecast devices.

### Prerequisites

This project depends on the following packages:

```
pychromecast
python-twitter
googlemaps
```


### Configuration

A "config.ini" file needs to be created at the root of the project. Please specify API keys and desired addresses for drive times in this file.

```
[google_maps]
key = <google maps api key>
start_address = <start address>
end_address = <end address>

[twitter]
access_token = '<twitter access token key>'
access_secret = '<twitter access secret key>'
consumer_key = '<twitter consumer key>'
consumer_secret = '<twitter consumer secret>'
```
