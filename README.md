# Slack Automation - WorkflowBuddy

[Workflow Builder](https://slack.com/features/workflow-automation) is great! _Except_ it's got a very limited selection of built-in Slack triggers _(**4**: shortcut, emoji reaction, new channel member, webhook)_ and **_VERY_** limited selection of built-in Slack actions _(**2**: send a message, send a form)_. You can get creative and do a lot with these building blocks, but what if you want to do more?

🥳 ✨ **Ta-da!** ✨

This Slack App acts as an extension of Workflow Builder, providing access to significantly more Slack triggers (such as `app_mention`, `channel_created`, etc.) and expanding the suite of Steps available. The most important is the `webhook` functionality, which enables users to plug their Slack Workflow Steps into almost any other application.

- **WorkflowBuddy**
  - [Available Triggers](#🏁🎬-available-triggers)
  - [Available Steps](#🏃available-steps)
  - [Use Cases](#use-cases)
- [Run Locally](#run-locally) - _test me out!_
- [Development](#development)
- [Deployment](#deployment) 

---

## 🏁🎬 Available Triggers

All [Slack events](https://api.slack.com/events) proxied through to any **_webhook-triggered_** Workflows.\* See _"Templates to save time"_ for copyable webhook starting points.

_*While WorkflowBuddy code will work out of the box as an event proxy, you will need to update your app's OAuth scopes & event subscriptions for your new events, as well as save the webhook event from your Workflow in the config._

![Visualizing the Slack event proxy](/static/workflow-buddy-event-proxy.png)

### Templates for Event Triggers

When using **Workflow Builder Webhooks**, it requires allow-listing any data keys you want to use from the request body. To make this easier, in `event_trigger_example_workflows/`, you can find templates that already have all the requisite keys already in place, matching the [core payload from the Slack API](https://api.slack.com/events?). Currently the wrapping payload is not included, but could be an easy contribution in the future.

## 🏃Available Steps

The utilities currently available within WorkflowBuddy for use as Workflow Steps. To see the exact inputs & outputs without loading up Workflow Builder, see [constants.py](https://github.com/happybara-io/WorkflowBuddy/blob/main/constants.py)

### Send a Webhook

Send data from your Slack Workflows to almost any service. You can trigger GitHub repos, Jenkins Builds, Salesforce actions, you name it.

### Random Int

Generate a random int in the range [`lower_bound`-`upper_bound`], inclusive.

### Random UUID

Generate a random UUID with [Python's standard library](https://docs.python.org/3/library/uuid.html).

### (Slack) Create a channel

- [API Method](https://api.slack.com/methods/conversations.create)

This action will create a new channel with your specified name, then return the `channel_id` as both text & the `channel` type so it can be used in Slack's built-in functions.

### (Slack) Find user by email

- [API Method](https://api.slack.com/methods/users.lookupByEmail)

Get a user based on their Slack email. Returns the user as both a text `user_id` and a `user` type so it can be used in Slack's built-in functions.

### More to come ....

🥱🔃

Potential ideas seen in the wild for other automation use-cases ([Zapier](https://zapier.com/apps/categories/zapier-tools) and [n8n](https://docs.n8n.io/integrations/builtin/core-nodes/) are good sources):
- Wait/delay state
  - Workflow Builder does not have a convenient way to add a pause step - Workflows are long-running, so it should be no problem to have some wait action that doesn't run `complete()` until the duration has passed. The best solution for this may vary by hosting provider, or by integrating with a 3rd-party service.
- Filter/conditional stop
  - If a certain condition is not met, stop the workflow. Handy if you only want it to fire on certain conditions and the trigger isn't granular enough.
- Send email and/or SMS
  - Might be hard if they want it sent from their own address vs a generic SendGrid-type account.
- Calendar invites/sending with a link?
  - This seems like it's mostly covered through the `Send a message` built-in.
- Suggested Slack actions based on Zapier
  - Add reminder
  - Invite user to channel
  - Send channel message (slack built-in)
  - Send direct message (slack built-in)
  - Create channel
  - Set channel topic (! Cannot be done with a Bot token, only user token 😔)
  - Update profile
  - Set status
  - Find message
  - find user by ID
  - Find user by name
  - Find user by username


## Use Cases

What can you do with these extra triggers and actions?

### Replace the legacy Outgoing Webhooks 

Slack used to offer [Outgoing Webhooks](https://slack.com/apps/A0F7VRG6Q-outgoing-webhooks?tab=more_info) as a way to listen for new messages/Trigger Words in Slack messages and then fire a webhook to external URLs.

It has a warning at the top though _"Please note, this is a legacy custom integration - an outdated way for teams to integrate with Slack. These integrations lack newer features and they will be deprecated and possibly removed in the future."_. To avoid any issues, you can alternatively use WorkflowBuddy to listen for `message`**\*** events & then use it's `Step: Send a Webhook` to accomplish the same thing.

**\*** _WorkflowBuddy doesn't yet have the same granularity for filtering events, but it is on the potential roadmap._

---

## Development

- [Bolt Python](https://slack.dev/bolt-python/)

## Run locally

Run the app locally & connect to your workspace Slack app.

### Setup
- [Create your Slack app](https://api.slack.com/reference/manifests#creating_apps) from the `slack_app_manifest.yml` file.
- Create a `.env` file that looks like:
  ```
  SLACK_BOT_TOKEN=xoxb-********
  SLACK_SIGNING_SECRET=********
  ```

### Run

Use [`ngrok`](https://ngrok.com) to tunnel your local port to the public internet, then run the server with Docker.

```
make ngrok
# (in a separate terminal)
make up
```

### Local Development

Alternative to running it with Docker, run the development server.

- `poetry install` (or install with your preferred Python tool using the `requirements.txt`).
- _(in a separate terminal)_ `make ngrok`.
- `poetry shell` so all our environment variables are easy.
- Run the local dev server with `./run.sh`, or a "prod" server with `./run-prod.sh`.
- Update the Slack App console with new `ngrok` address - for [Event Subscriptions](https://api.slack.com/apps/A040W1RHGBX/event-subscriptions?), Interactivity - this is easiest done by updating the `slack_app_manifest.yml` file and then copying it onto the Manifest page in Slack App console.
- (_Testing Webhooks_) [Handy tool to debug with](https://webhook.site)


### How it works

For Slack events, this app basically just acts as a proxy. As long as the event is added to the bot's OAuth scopes, it should be able to proxy it through to your **Workflow Builder** flow. 

For the new actions, it registers a **Workflow Builder Step** - unfortunately each app is limited to 10 registered with Slack. To get around that limitation, we have the user select from a static select list of actions that have been implemented on the server, then update the modal to give them the appropriate options. For example, if the user wants to `Send a webhook`, we'll then update the modal to have an input for the Webhook URL, and a text box for the body they want to send.

Config data (basically just webhooks for now) is persisted on disk using [Python Shelve](https://docs.python.org/3/library/shelve.html#module-shelve).

### Future Work

As you may have noticed, this is a P.o.C. There is no resiliency baked into this application yet, so don't throw anything mission critical on it yet. A non-exhaustive list of updates it would benefit from:

- Server needs to be productionized and easy to deploy - Docker-Compose is recommended route.
  - Write up a guide on how to deploy it to [Fly.io](https://fly.io) or similar easy deploy tools.
- Sending webhooks should have a simple retry mechanism in place, in case it just needs a few seconds before things work hunky dory.
- Incoming actions should be placed into a resilient queue, that way events aren't lost in the case of downstream failure response, server outage, or etc. 
  - A DB like SQlite can act as a queue in a pinch, so long as you setup an easy cron option. Rather than figuring out how to setup Celery with Python, why not use one of those services that will send you a webhook on a cron schedule, so all you have to write is an endpoint. [Cronhooks](https://cronhooks.io/) is one such aptly named service.
- Tracking the timestamps of when the workflows were kicked off and also whether they succeeded or failed would be a nice touch, but that's a lot of data for a PoC app.

---

## Deployment

Putting your server somewhere more useful than your local machine.

### Fly.io

- Add secrets from `.env.example` using [`flyctl secrets`](https://fly.io/docs/reference/secrets/#setting-secrets). Same secrets setup as in Development section.
- (Optional) update `fly.toml` config settings.
- Run `fly deploy`.
- ⚠️ _Using a very simple cache + JSON file to persist webhook config data - it's not very robust, so highly recommend keeping a copy of the JSON file as backup to easily import if config is destroyed._

### Others

TBD.
