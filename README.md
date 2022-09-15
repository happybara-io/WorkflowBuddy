# Slack Automation - WorkflowBuddy

Workflow Builder is great! Except it's got a very limited selection of built-in Slack triggers (shortcut, emoji reaction, new channel member, webhook) and VERY limited selection of built-in Slack actions (send a message, send a form). You can get creative and do a lot with these building blocks, but what if you want to do more?

🥳 ✨ Ta-da! ✨

This Slack App acts as an extension of Workflow Builder, providing access to significantly more Slack triggers (such as `app_mention`, `channel_created`, etc.) and expanding the suite of actions available. The most important is the `webhook` functionality, which enables users to plug their Slack Workflow steps into other applications.

## Setup

- Create a `.env` file that looks like:
  ```
  SLACK_BOT_TOKEN=xoxb-********
  SLACK_SIGNING_SECRET=********
  ```
  (TEMPORARILY)
  _Until a real datastore is configured, you will temporarily also need the `EVENT_APP_MENTION_WEBHOOK_URL` variable set in the `.env` file._
- `poetry install` (or install with your preferred Python tool using the `requirements.txt`)

## Development
- `poetry shell` so all our environment variables are easy
- (in a separate terminal) Run `ngrok http 3000` to get a public domain address - [Ngrok Dashboard](https://dashboard.ngrok.com)
- Run the local server with `./run.sh`
- Update the Slack App console with new address - for [Event Subscriptions](https://api.slack.com/apps/A040W1RHGBX/event-subscriptions?), Interactivity
- (_Testing Webhooks_) [Handy tool to debug with](https://webhook.site)

## Production Deployment

TBD. Likely will be a Docker-Compose app that's easy for anyone to run almost anywhere.

## Templates to save time

When using **Workflow Builder Webhooks**, it requires allow-listing any data keys you want to use from the request body. To make this easier, in `event_trigger_example_workflows/`, you can find templates that already have all the requisite keys already in place, matching the [core payload from the Slack API](https://api.slack.com/events?). Currently the wrapping payload is not included, but could be an easy contribution in the future.

## How it works

For Slack events, this app basically just acts as a proxy. As long as the event is added to the bot's OAuth scopes, it should be able to proxy it through to your **Workflow Builder** flow. 

For the new actions, it registers a **Workflow Builder Step** - unfortunately each app is limited to 10 registered with Slack. To get around that limitation, we have the user select from a static select list of actions that have been implemented on the server, then update the modal to give them the appropriate options. For example, if the user wants to `Send a webhook`, we'll then update the modal to have an input for the Webhook URL, and a text box for the body they want to send.

## Future Work

As you may have noticed, this is a P.o.C. There is no resiliency baked into this application yet, so don't throw anything mission critical on it yet. A non-exhaustive list of updates it would benefit from:

- Server needs to be productionized and easy to deploy - Docker-Compose is recommended route.
  - Write up a guide on how to deploy it to [Fly.io](https://fly.io) or similar easy deploy tools.
- Need a datastore that isn't environment variables - 🤔 or do I? 😄
  - Ideally user can CRUD their mapping of workflows to events from the App Home.
- Sending webhooks should have a simple retry mechanism in place, in case it just needs a few seconds before things work hunky dory.
- Incoming actions should be placed into a resilient queue, that way events aren't lost in the case of downstream failure response, server outage, or etc. 
  - A DB like SQlite can act as a queue in a pinch, so long as you setup an easy cron option. Rather than figuring out how to setup Celery with Python, why not use one of those services that will send you a webhook on a cron schedule, so all you have to write is an endpoint. [Cronhooks](https://cronhooks.io/) is one such aptly named service.
- 