# Slack Automation - Local Bolt Project

Testing locally with Bolt and Ngrok to try learning some new things.


## Steps to run

- `poetry shell` so all our environment variables are easy
- (in a separate terminal) Run `./ngrok` to get a public domain address - [Ngrok Dashboard](https://dashboard.ngrok.com)
- Run the local server with `./run.sh`
- Update the Slack App console with new address - for [Event Subscriptions](https://api.slack.com/apps/A040W1RHGBX/event-subscriptions?), Interactivity

## Notes during setup of demo

- [Slack Guide to get setup over HTTP](https://slack.dev/bolt-python/tutorial/getting-started-http)
- Demo requirements doesn't even include their own package, confusing
- Slack bolt uses same `/slack/events` path by default for both Events and Interactivity
