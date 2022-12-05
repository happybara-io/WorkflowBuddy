# Workflow Buddy - Super powers for Workflow Builder

_| 📂 Open-source | [🧪 Installable Demo App](#demo-app) | [🤖 Hosted for you](https://tally.so/r/mVLKkj) | [💡 Support](#support) |_

---
## Testimonials

>🗣 _"Workflow Buddy is such an enabler for us. It’s exactly what I hoped Workflow Builder originally was." - [iCulture.nl](https://www.iculture.nl/)_

> 🗣 _"It’s like a mini Zapier in Slack… By using Buddy I was able to remove many unnecessary formatting steps from Zapier, effectively saving me money." - Feedback during Alpha_

---

**[Workflow Builder](https://slack.com/features/workflow-automation) is great!**

**... and it has great potential, too!** 😅

The current implementation you get out of the box is a bit boxed in by:

- a small selection of built-in Slack triggers (`5`)
  - _shortcut, new channel member, emoji reaction, schedule, webhook_
- a **_VERY_** limited selection of built-in Slack actions (`2`)
  - _send a message, send a form_

_You can get creative and do a lot with these building blocks, but what if you want to do **more**?_

### 🥳 ✨ **Ta-da!** ✨

**This Slack App acts as an extension of Workflow Builder, providing access to significantly more Slack triggers (such as `app_mention`, `channel_created`, etc.) and expanding the suite of Steps available.**

⚡ The most important **Step** this app adds is the `Outgoing Webhook`, which enables users to integrate their Slack Workflow Steps with almost any other application.

> **[ℹ️]** Beta Disclaimer:
>
> This code is in beta stage on it's way to a stable v1. It's fully functional, but would benefit from resiliency features like improved handling for upstream API errors, etc. that let it handle higher volume use-cases.
>

- **About**
  - [Demo Videos](#demos)
  - [Available Event Triggers](#-available-triggers) - `+Many`
  - [Available Steps](#-available-steps) - `+15`
  - [Common Use Cases](#-use-cases)
- **Quick Starts/ Installation** - 🎉 _test me out!_ 🧪
  - [Installing your own Buddy](#running-workflow-buddy) - (5-30 mins)
  - [(Beginner) Simple Workflow](#beginner-quickstart-create-a-simple-workflow) - (~10 mins)
  - [(Advanced) Try New Event Triggers](#advanced-quickstart-new-event-triggers) - (~25 mins)
  - [(Advanced) Try New Steps](#advanced-quickstart-run-all-new-steps) - (~25 mins)
- [FAQ](#faq)
- [Support](#support)
- [Development](#development)

---

## Support

Want to get rockin' with Workflow Buddy, but running into trouble? You have a number of resources to help you out:

- 📚 Read the docs - _in this README, and the [wiki](https://github.com/happybara-io/WorkflowBuddy/wiki)_
- 👬 Search through or ask a question in the [Community Discussions](https://github.com/happybara-io/WorkflowBuddy/discussions) - _no question is too small_.
- 📩 Send an email to [support@happybara.io](mailto:support@happybara.io). 
- 🙋‍♀️ If you found a bug; open a [new GitHub issue](https://github.com/happybara-io/WorkflowBuddy/issues/new/choose). _⚠ If in doubt, please use the Discussions rather than Issues._

---

## Demos

_Hate reading and would rather see videos of it in action?_

- [A ~3min video demo](https://github.com/happybara-io/WorkflowBuddy/blob/main/demos/app_mention_e2e_flow.md) showing a [custom event](#-available-triggers) triggering a Workflow which runs the majority of the [available Step actions](#-available-steps).
- [A ~3min video demo](https://github.com/happybara-io/WorkflowBuddy/blob/main/demos/importing-from-trigger-and-outgoing-webhooks.md) showing how to go from [downloaded template](#templates-for-event-triggers) to triggering a Workflow that sends an [`Outgoing Webhook`](#send-a-webhook), along with a bonus of showing how to [proxy slack events to another service](#proxy-slack-events-to-another-service).

---

## ⛏ Use Cases

What can you do with these extra triggers and actions?

### Trigger Slack Workflows with (almost) any event

Expand beyond the limited number of events that Workflow Builder comes with out of the box.

### Replace the legacy Outgoing Webhooks

Slack used to offer [Outgoing Webhooks](https://slack.com/apps/A0F7VRG6Q-outgoing-webhooks?tab=more_info) as a way to listen for new messages/Trigger Words in Slack messages and then fire a webhook to external URLs.

It has a warning at the top though _"Please note, this is a legacy custom integration - an outdated way for teams to integrate with Slack. These integrations lack newer features and they will be deprecated and possibly removed in the future."_. To avoid any issues, you can alternatively use WorkflowBuddy to accomplish the same thing (in 2 ways!).

Enable listening for `message`**\*** events, then either directly proxy the event to your webhook (by adding it to the `Event-Webhook Map` in App Home) or use the `Step: Send a Webhook` as part of a longer Workflow.

**\*** _WorkflowBuddy doesn't yet have the same granularity for filtering events, but it is on the potential roadmap._

### Reuse the same Workflow for multiple channels across a Workspace

Slack Workflows are currently tied to a single channel, which can be a hold up if you want to track events across multiple. To stick within Workflow Builder, you need to download and duplicate the same workflow for every possible channel you want..... or just use Workflow Buddy and proxy all the events to a single Workflow.

Example for `reaction added`:

- Invite Workflow Buddy to each of the channels you want it to listen for reactions in.
- Set up your desired Workflow as a `Webhook-triggered` in Workflow Builder. Publish and copy the URL.
- In the Workflow Buddy App Home, configure the `reaction_added` event with the Webhook from previous step.
- 🧪 Test by reacting to some messages! Any channel the bot has been invited to will send their events through Workflow Buddy - and onward to your Workflow.

### Start other Worflows from the middle of a Workflow

With the power of webhooks, you can use actions and outcomes in the middle of a Workflow to start other Slack Workflows or automation in other tools. E.g. send a receipt to a customer while you're in the middle of processing the Workflow.

### Have as many events as you want trigger a Workflow

With Slack Workflow Builder, you can only configure a **single** event to trigger your Workflow (e.g. _person added to a specific channel). Workflow Buddy has no restrictions on the number or variety of `event->webhook` mappings you configure. Maybe you want all the `channel_*` event types to kick off a workflow, or you want to have incoming events sent in parallel to a [Webhook testing site](https://webhook.site) while you're debugging your workflow.

> ⚠: _"Webhook workflows are limited to one request per second."-[src](https://slack.com/help/articles/360041352714-Create-more-advanced-workflows-using-webhooks)._ You can enable numerous events, but you also can't hammer the service with 50K workflow executions, so be careful when using the high-volume events like `message`.

### Send data from Slack Workflow to other apps

Use the customizable `Outgoing Webhook` Step as part of a workflow and fill the JSON body with relevant context. Examples might be triggering Airtable automations when your Workflow is finished, or kicking off GitHub Actions.

### Proxy Slack events to another service

Workflow Buddy was originally intended for expanding the available Workflow Builder triggers within Slack, but it can also be used to proxy Slack events to another service - bypassing Workflow Builder entirely. This can be done by following parts of the [New Event Triggers Guide](#advanced-quickstart-new-event-triggers). You can skip creating a workflow, then after double checking your OAuth scopes are all set, you can `Add` a new event-> webhook mapping and connect the event to your external services URL.

> ℹ️: When using in this advanced manner, you'll want to set your webhook configuration setting `raw_event: true`.  See [Raw Event in Options](#global-options).

### Your great idea here

There are tons of awesome use cases we haven't thought of yet, submit a PR or reach out to tell us about yours!

---

## 🏁🎬 Available Triggers

All\* [Slack events](https://api.slack.com/events) proxied through to any **_webhook-triggered_** Workflows.\*\* See _"Templates to save time"_ for copyable webhook starting points.

> _\*During alpha stage, only a small number of events have been implemented, but goal is to quickly update to handle 80-90% of uses cases, and eventually 100%._
> _\*\* While WorkflowBuddy code will work out of the box as an event proxy, you will need to update your app's OAuth scopes & event subscriptions for your new events, as well as save the webhook event from your Workflow in the config._

![Visualizing the Slack event proxy](/assets/workflow-buddy-event-proxy.png)

### Events

The events that have been tested and are known to be working - other Slack events should work, but have not had the same testing done.

`Options` is the keys you can add to the Webhook config options through App Home. If the option isn't visible in `Add` modal, then it can be added directly by:

- `Export` the config.
- Edit it to add your desired `Options`.
- `Import` the updated config.

#### Global Options

Options that work the same across event types.

- `raw_event`: By default, Workflow Buddy will flatten & limit the JSON it receives to fit with the [Slack limitations](#templates-for-event-triggers) of 20 variables and no nested data. Set this to `true` to turn off the transformation.

#### **app_mention** - [_docs_](https://api.slack.com/events/app_mention)

- [x] happy path tested
- [x] template: [`event_trigger_example_workflows/trigger_app_mention.slackworkflow`](https://raw.githubusercontent.com/happybara-io/WorkflowBuddy/main/event_trigger_example_workflows/trigger_app_mention.slackworkflow).

Listen for when your bot gets mentioned across the workspace.

**Options:**

- `filter_channel` - [Channel ID](#how-to-get-a-channel-id). If you want to filter down to a single channel. Example use case: `Workflow triggered by mentioning bot in a specific channel`.

#### **channel_created** - [_docs_](https://api.slack.com/events/channel_created)

- [x] happy path tested
- [x] template: [`event_trigger_example_workflows/trigger_channel_created.slackworkflow`](https://raw.githubusercontent.com/happybara-io/WorkflowBuddy/main/event_trigger_example_workflows/trigger_channel_created.slackworkflow).

Listen for new channels being created.

#### **reaction_added** - [_docs_](https://api.slack.com/events/reaction_added)

- [x] happy path tested
- [x] template: [`event_trigger_example_workflows/trigger_reaction_added.slackworkflow`](https://raw.githubusercontent.com/happybara-io/WorkflowBuddy/main/event_trigger_example_workflows/trigger_reaction_added.slackworkflow).

If you only want a single reaction type (e.g. 😀) in a single channel, then you'll want to just use the Workflow Builder built-in. The Workflow Buddy version provides a bit more functionality.

- Listen to **All** reactions coming in - not just a single.
- Listen across every conversation Workflow Buddy is apart of - not just a single channel. Tested in public & private channels.

**Options:**

- `filter_react` - the emoji/reaction you want to let through.
- `filter_channel` - [Channel ID](#how-to-get-a-channel-id). If you want to filter down to a single channel. Example use case: `Workflow triggered by any emoji reaction in a specific channel`.

### Templates for Event Triggers

When using **Workflow Builder Webhooks**, it requires allow-listing any data keys you want to use from the request body. To make this easier, in `event_trigger_example_workflows/`, you can find templates that already have all the requisite keys already in place, matching the [core payload from the Slack API](https://api.slack.com/events?).

> ⚠️**Limitations**
>
> - [Slack restrictions](https://slack.com/help/articles/360041352714-Create-more-advanced-workflows-using-webhooks)
>   - Max of `20` variables allowed.
>   - Cannot handle nested JSON.
>   - Workflow fails if all variables not present.
> - Workflow Buddy
>   - Only a small number of templates have been completed so far, good contribution opportunity!
>   - Currently the [wrapping payload](https://api.slack.com/types/event) is not included, but it could be an easy contribution in the future.

## 🏃 Available Steps

The utilities currently available within WorkflowBuddy for use as Workflow Steps. To see the exact inputs & outputs without loading up Workflow Builder, see [constants.py](https://github.com/happybara-io/WorkflowBuddy/blob/main/constants.py).

![User choosing which action they want in workflow](/assets/workflow-buddy-choose-step-action-modal.png)

### Send an Outgoing Webhook/ HTTP Request

Send data from your Slack Workflows to almost any service. You can trigger GitHub repos, Jenkins Builds, Salesforce actions, you name it.

### Extract Values from JSON

Use [`JSONPATH` expressions](https://github.com/h2non/jsonpath-ng) to extract data from JSON strings in your Workflows to use as variable in other **Steps**. Common use case is to parse a value out of an HTTP response body.

_Need multiple values? For now, you can just use this Step multiple times in a Workflow for each value you need. In the future, we plan to support multiple in one Step._

### Wait for human | approval | manual completion

Many names to describe it. In short, have your workflow wait in an `In progress` state until a human has taken action to either `Complete`➡ and let the Workflow continue, or `Fail`❌ it and stop the flow.

### Wait for Webhook/ HTTP Request

Have your workflow wait in an `In progress` state until it receives a webhook from an external service. You can choose to either `Complete`➡ and let the Workflow continue, or `Fail`❌ it and stop the flow.

Example body Workflow Buddy expects:

```
{
  "execution_id": "4364223353762.667214953526.b8f41739087702effd5ac3b0b514006f",
  "sk": "RTPLSJVIBcmCAUcnUtbI",
  "mark_as_failed": true,
  "err_msg": "My sevice blew up!"
}
```

_How do you get the execution ID?_ When saving the step, you will define a URL for Workflow Buddy to send the required data to. You could also get it from the `Manual Complete` step if it better fits your use case.

### Wait/ Pause

Have your workflow wait for

### Random Integer

Generate a random integer in the range [`lower_bound`-`upper_bound`], inclusive.

**Example**: Given `5` - `15`, would output random value like `11`.

### Random UUID

Generate a random UUID with [Python's standard library](https://docs.python.org/3/library/uuid.html).

**Example**: `a3b45ac2-d1ba-4c54-9e1c-0d51983ec952`.

### (Slack) Random Member Picker

- [Core API Method](https://api.slack.com/methods/conversations.members)

Choose a random sample of 1+ non-bot users from a conversation. Each user is available as an individual variable in future Workflow Steps.

### (Slack) Create a channel

- [Core API Method](https://api.slack.com/methods/conversations.create)

This action will create a new channel with your specified name, then return the `channel_id` as both text & the `channel` type so it can be used in Slack's built-in functions.

### (Slack) Find user by email

- [Core API Method](https://api.slack.com/methods/users.lookupByEmail)

Get a user based on their Slack email. Returns the user as both a text `user_id` and a `user` type so it can be used in Slack's built-in functions.

### (Slack) Get Email From User ID

Get email based on a Slack user ID. Useful when you have plain text user IDs in your Workflow.

> _⚠ If your variable is a 'user' type, you already have access to the email and don't need to use this utility! To access, insert the variable into your input, then click on it - from there you can choose from mention `<@U1234>`, name `First Last`, or email `you@example.com`._

### (Slack) Schedule a message

- [Core API Method](https://api.slack.com/methods/chat.scheduleMessage)
- [Advanced formatting in Slack messages](https://api.slack.com/reference/surfaces/formatting)
Schedule bot messages to public channels up to 120 days in the future.

### (Slack) Set Channel Topic

- [Core API Method](https://api.slack.com/methods/conversations.setTopic)

Set the topic for any conversation that Workflow Buddy has been invited to.

### (Slack) Add Reaction

- [Core API Method](https://api.slack.com/methods/reactions.add)

Adds a reaction to a message, given the permalink URL. Works with the Slack built-in `Reaction Added` Workflow Trigger.

### (Slack) Find a Message

- [Core API Method](https://api.slack.com/methods/search.messages)

Query the Slack search and return the top result as Workflow variables.

> ⚠ The Slack search endpoint requires a User token, which will be based on whoever installed the Workflow Buddy app. Results will be constrained to what that user is able to search. If you are running into issues with the user token, please [Open an Issue 🐛](https://github.com/happybara-io/WorkflowBuddy/issues/new/choose).

### More to come

See [Issue #10](https://github.com/happybara-io/WorkflowBuddy/issues/10) for discussion on potential Step actions to add.

## Bonus Utilities

Occasionally I run into handy utilities that make life easier when building automations for Slack workspaces, and what better place than a toolkit like Workflow Buddy!

### Debug Mode

For any Workflow Buddy Step, you can enable `Debug Mode`, which will pause and send you a message with information about the `inputs` and metadata, then wait for you to click `Continue`.

[Learn More | Wiki](https://github.com/happybara-io/WorkflowBuddy/wiki/Debug-Mode)

### Shortcut: Inspect Message

A message shortcut that pulls up the associated metadata Slack has for it, including useful attributes like `team_id`, `user_id`, message `ts`, etc. Handy when being a Builder of Workflows or developing steps.

---

## 🏁 Quickstarts

Follow a walk-through to get a feel for what the system can do.

### Beginner Quickstart: Create a Simple Workflow

Let's open up Workflow Builder and put together a simple Workflow that starts from a [Slack Shortcut](https://slack.com/help/articles/360057554553-Take-actions-quickly-with-shortcuts-in-Slack), uses some of the simple utilities that Workflow Buddy provides, then sends you a message with the output.

> ⚠ If you don't already have a channel for testing purposes, go create one. We don't want to annoy any of your team mates with random messages.

> ℹ  _If you haven't yet, you'll need to get a [Buddy instance running + a Slack app](#running-workflow-buddy). Come back when you're ready._

- Open up Workflow Builder (Top left Workspace menu -> `Tools` -> `Workflow Builder`)
- Click `Create`.
- Give it a name, like `workflow buddy test`.
- Select `Shortcut` from the Trigger options.
- Select your **testing channel** as the location. Add the short name.

🙌 **Awesome!** You just built a minimal `no-op` (_do nothing_) workflow. Let's make it do something more fun!

- Add Step 1
  - Click `Add Step`. You should see a couple _Workflow Buddy_ actions available along with other Steps available in your workspace.
  - choose `Utilities` from _Workflow Buddy_. Then once the modal appears, change the drop down to `Random UUID`.
  - **Save!**
- Add Step 2
  - Click `Add Step` again.
  - Choose `Send a message`. In the modal, choose `Person who clicked...` as the recipient. In the **Message text** section, try `Insert a variable` and choose `Random UUID` from the dropdown to add it to your message text. Feel free to add any other sentences you want alongside the `UUID` variable.
    > _**What did we just do?**_
    >
    > - Slack lets you access the outputs of previous steps as **Variables**. Next to any text input box you will see that `Insert a variable` option. Sometimes it even lets you use them in drop downs, like when you selected the `Person who clicked..` - that's a variable representing anyone who clicks the workflow!
    > - The majority of Workflow Buddy actions will provide **Outputs** that you can use in future Steps - webhook response codes, random numbers, Slack users, etc. Try and get creative - sending a message with the info is only the beginning of possibilities. _How might you link multiple actions together with variables?_
    >
  - **Save!**
- Click `Publish`.

🧪 **The Workflow is now ready for testing!** Go to your test channel you added the Workflow to, open up the Shortcuts menu, and you should see your `Short name` you chose in the options. Click it!

If everything was correct, you should receive a message with a random UUID value and the text you wrote!

✅**You successfully created a Slack Workflow using Steps from both Workflow Buddy and Slack, awesome!**

_If you are looking to explore more advanced concepts like Triggers or advanced Workflow Buddy Steps, check out the **Advanced Quickstarts** below. Otherwise feel free to keep poking around on your own in Workflow Builder. There's endless possibilities, so **automate everything!**_

### Advanced Quickstart: Run All New Steps

Try out the new **Steps** by importing a Workflow that has all of them configured (except for ones that make changes to your Slack Workspace, like `Create a channel`. Don't want to cause any weird side-effects during your testing!).

> ℹ  _If you haven't yet, you'll need to get a [Buddy instance running + a Slack app](#running-workflow-buddy). Come back when you're ready._

- Download the Workflow template from `test_workflows/workflow_buddy_end_to_end_test_read_only.slackworkflow`[(link)](https://github.com/happybara-io/WorkflowBuddy/blob/main/test_workflows/workflow_buddy_end_to_end_test_read_only.slackworkflow), which contains all the basic functionality of Workflow Buddy Steps.
- Open Workflow Builder, `Import`, and `Publish` it!
- Click the `Edit` button on each of the configured Steps in the Workflow so you can see how each available action is configured. **Several require updates:**
  - You'll need to fill in a test email for `find by email`; do your own to start.
  - In `Send a webhook`, update the URL to be `https://<your ngrok or server URL>/webhook` to hit your own Workflow Buddy server's extra endpoint.
  - In `Schedule message`, you'll likely need to update the `timestamp`.
- Run the Workflow and check the outputted message for details of the execution.

✅ **That's it!**

- You now have the abiltity to use all of the Workflow Buddy Steps for your Workflows now!

**Go forth and automate!**

### Advanced Quickstart: New Event Triggers

We're gonna start with a simple event we can easily control: `app_mention` _(when your bot is `@WorkflowBuddy` in a channel)_. We will use that event to kick off a simple Workflow that just sends us a message.

> ℹ  _If you haven't yet, you'll need to get a [Buddy instance running + a Slack app](#running-workflow-buddy). Come back when you're ready._

- **First we'll set up the Workflow we want triggered - in Workflow Builder.**
  - Download the Workflow template from `event_trigger_example_workflows/trigger_app_mention.slackworkflow`[(link)](https://github.com/happybara-io/WorkflowBuddy/blob/main/event_trigger_example_workflows/trigger_app_mention.slackworkflow). You can also start from scratch - the only _**critical**_ step is to choose `Webhook` as your new Workflow's event trigger.
  - Open Workflow Builder, `Import` (or create), and `Publish` it to get your new `Webhook URL`.
- **Open Workflow Buddy App Home to connect Workflow -> Event Trigger.**
  - Go to the `App Home` of Workflow Buddy _(or whatever you named your app)_ and click `Add`. It will display a modal asking you to fill out your desired event trigger & the `Webhook URL` from first step.
- **Test it!**
  - From any public channel, post a message with `@WorkflowBuddy` _(or whatever you named your app)_.
  - That message will cause an `app_mention` event to be sent from Slack to your instance of the Workflow Buddy server.
  - If you correctly configured the `event->webhook` mapping, the event will then be proxied to the test Workflow you added in the first step.

✅**That's it!**

- You now have the abiltity to use all sorts of Slack events as Triggers for your Workflows now! _(⚠ So long as you have given your Slack app the OAuth permissions to use them)._

**Go forth and automate!**

---

## FAQ

### How to get a channel ID?

- Navigate to the desired channel in Slack, then click it's name at the top to open `Channel details`.
- Scroll to the bottom of that modal, and you'll see a copyable channel ID that looks like:

  `Channel ID: GMZE58GD9`

### Is this a replacement for Workflow Builder?

❌ No! This acts as a complement to Workflow Builder, enhancing it's functionality to do even more awesome things.

### Isn't Slack going to eventually add this functionality to Workflow Builder?

Maybe, but until then, you have an option rather than waiting impatiently. Plus, since it is an extension of Workflow Builder, it won't stop working if Slack decides to add new functionality to the core tool. For those unaware, Slack is planning to release [conditional logic and other features in Q1 2023](https://techcrunch.com/2022/09/01/slack-gains-new-automation-features-including-conditional-logic-for-workflows/?guccounter=1).

---

## Hosted

Don't want to host servers yourself, but still want to use Buddy? Happybara plans to release a hosted version in the near future.

[🏄‍♀️ Snag your spot on the waitlist!](https://tally.so/r/mVLKkj)

## Running Workflow Buddy

> 🧪 _Just want to experiment? Install the [demo app](#demo-app) to your Slack workspace and skip setting up servers until you're ready. You can skip to [🎉 Use the app](#-use-the-app) to follow **guided quickstarts**. If you get stuck, check out your [💡 support resources](#support)._

You have several options to run a Buddy server: locally on your computer, self-hosted on a cloud service, or [hosted by Happybara](#hosted) _(coming soon)_.

To run a Buddy server yourself, you will:

1. Create a Slack app through the [Slack website](https://api.slack.com/apps) (this creates the access tokens so you can talk to Slack).
2. Run a Buddy server either **A)** on your laptop, or **B)** in the cloud.
3. Update Slack connection info.
4. Use the bot through your regular Slack desktop! 💃

### Demo App

There is a demo version of Workflow Buddy that can be [installed to your workspace](https://workflow-buddy-demo.fly.dev/slack/install) rather than setting up Slack apps & servers just to sample it.

Once installed, you can skip to [🎉 Use the app](#-use-the-app) to follow **guided quickstarts** to learn what is possible with Workflow Buddy.

> ⚠️
> This app is intended for initial testing only! Think of it like the free samples at Costco - gives you a taste, but not meant for a whole meal. Once you've tried out Workflow Buddy, you should look into the hosting options below since the demo app does not have guarantees around uptime, long-term data storage, etc.
>

### Slack App Setup

- **Copy `slack_app_manifest.template.yml` to `slack_app_manifest.yml`**.
  - This lets you make any changes to the app you want, while making it easy to pull updates to the repo without conflicts.
  - _(Optional) Change the app name, but only if you don't like `Workflow Buddy`🙁._
- **[Create your Slack app](https://api.slack.com/reference/manifests#creating_apps) from the `slack_app_manifest.yml` file.**
  - _⚠ MAKE SURE TO CLICK `from an app manifest` WHEN THE MODAL POPS UP!_.
  - After a couple simple confirmation modals to go through.
  - Go to the `OAuth & Permissions` section and click `Install App` to grant permissions for your new app on the workspace. This will generate the access tokens you will need for the next step.
- **Now create a `.env` file in your repo. We will be populating it with values from the Slack App you created.**
  - Get the `SLACK_BOT_TOKEN` & `SLACK_USER_TOKEN` from the `OAuth & Permissions` tab of your Slack app.
  - Get the `SLACK_SIGNING_SECRET` from the `Basic Information` tab of your Slack app.
  - The final result should look like:

    ```
    SLACK_BOT_TOKEN=xoxb-********
    # should only be needed if you want to use the 'Find a Message' action
    SLACK_USER_TOKEN=xoxp-********
    SLACK_SIGNING_SECRET=********
    # only oauth demo app should need
    SLACK_CLIENT_ID=********
    SLACK_CLIENT_SECRET=********
    ```

- **Next, you'll spin up the two local servers or a cloud server.**

> ⚠ There may be a warning about `request_url` verification - you can ignore that until we have spun up our local server and proxy (or our cloud server). Once that's done we will update in the Slack App website with your URLs.

### A. Run local Buddy

To run the Slack app locally you will:

1. ✅ Create a Slack app through the [Slack website](https://api.slack.com/apps) (this creates the access tokens so you can talk to Slack).
2. 📌 Run a local server on your laptop either using `Python` or `Docker` with the credentials you got in step `1`.
    - _If you use GitHub CodeSpaces for development, you can skip running a proxy tool, because they will port-forward for you._
3. Run a proxy tool that lets Slack talk to your `localhost` (local server).
4. Update Slack connection info.
5. Use the bot through your regular Slack desktop! 💃

#### Run Local: App Server

The easiest way to run the server is with Docker, though you can also run it with Python directly.

##### Run with the server with `Docker`

- `make up`

##### Run the server with `Python`

Another choice! Can either use [Poetry](https://python-poetry.org), or any build tool that understands `requirements.txt` that you're comfortable with.

- `Poetry`
  - `poetry install`
  - `poetry shell` (activates virtual environment)
- **OR** _< insert your favorite python build tool like `pip`, `Pipenv`, etc.>_
  - Install dependencies from `requirements.txt`
  - Activate a virtual environment
- With dependencies in place, run the local dev server with `./run-dev.sh`, or a "prod" server with `./run-prod.sh`.

🔁 You're almost there! Either way you chose, you should see a server waiting for requests. One last step and you can use your Slack app.

#### Run local: Proxy server

- Use [`ngrok`](https://ngrok.com) to tunnel your local port to the public internet. You can either download through a package manager and have it show up in your `$PATH`, or unzip the file and execute it directly `./ngrok`.
 _(⚠ in a separate terminal from your server)_

  ```
  # if you installed with Brew or similar
  make ngrok
  # OR if you just unzipped the file somewhere on your machine
  ./ngrok http 4747
  ```

- You should see a black screen with a bunch of info printed on it. That's good!
- Copy the `ngrok` forwarding URL that shows up, e.g. `https://4342423423.ngrok.io`

### B. Cloud Buddy

To self-host Buddy in the cloud, you will:

1. ✅ Create a Slack app through the [Slack website](https://api.slack.com/apps) (this creates the access tokens so you can talk to Slack).
2. 📌 Run a server at a cloud provider.
3. Update Slack connection info.
4. Use the bot through your regular Slack desktop! 💃

_If you get stuck, check out your [💡 support resources](#support)._

#### Cloud: Fly.io

You will need to create an account with cc details💳, though this should run on the free tier. You will then need to [install the `flyctl`](https://fly.io/docs/flyctl/installing/) tool and `flyctl auth login` so it gets connected.

- Copy `fly.template.toml` to `fly.toml`. Open `fly.toml` and customize the _app name_ on the first line of the file.
- 🥂 Run `flyctl launch` to get the app initialized with _Fly.io_. Choose `No` when it asks _"Would you like to deploy now?"_.
  - _You can choose any name you want for it, it won't be visible except in your [Fly dashboard](https://fly.io/dashboard/personal)._
- If you want your **data to persist between deployments**:
  - Create a volume for your instance. I set this to 1 GB, but you get up to 3 GB on the free tier. I also picked `ord` since I'm in the US, but pick any [region near you](https://fly.io/docs/reference/regions/).
    `flyctl volumes create workflowbuddy_vol --size 1 -r ord`
  - _(Optional, if using alternate name)_ Ensure `fly.toml` has the mount:

    ```
    [mounts]
        source="workflowbuddy_vol"
        destination="/usr/app/data/"
    ```

  - _(Optional)_ update `fly.toml` config settings.
- Add secrets from `.env` _(documented above)_ to the Fly environnment using [`flyctl secrets`](https://fly.io/docs/reference/secrets/#setting-secrets).
  - For each one, run: `flyctl secrets set <name>='<secret>'`.
  - 🚀 Finally, get a running app with `flyctl deploy`!
    - _If you run into issues with remote builders, you can always do it locally with `flyctl deploy --local-only`._

> ⚠️ _Currently it uses using a very simple cache + JSON file to persist webhook config data - it's not very robust, so **highly recommend** using the `Export` function to save a backup to easily `Import` if config is destroyed._

##### Updating Workflow Buddy on Fly

Currently the recommended best practice for updating Workflow Buddy:

- _(Optional)_ Backup previous config.
  - In Slack, go to `@Workflow Buddy` _App Home_ and `Export` any existing configurations, save them to a local file as a backup.
- _**(if necessary)**_ manually create any volumes that hadn't existed before. See notes above^.
- `cd` to your cloned WB repo. Run `git pull` for the latest updates.
  - If there were changes to `slack_app_manifest.template.yml`, you'll need to update [your Slack app](https://api.slack.com/apps/) with the latest and greatest.
  - If there were changes to the [secrets in Setup](#slack-app-setup), you will need to add those like was done above in [Cloud: Fly.io](#cloud-flyio).
- Run `fly deploy` to put your changes in to the wild!

#### Cloud: Other hosting providers

- [Serverless/ Cloudflare Workers was suggested](https://github.com/happybara-io/WorkflowBuddy/issues/29)
TBD.

### Update Slack connection info

Now we have a Slack app & a Workflow Buddy server running, we just need to make sure they can talk to each other!

- Update the Slack API site with your new ngrok or web server URL in 2 spots - [**Event Subscriptions**](https://api.slack.com/apps/A040W1RHGBX/event-subscriptions?), & **Interactivity**.
  - this is easiest done by updating the `slack_app_manifest.yml` file and then copying it onto the Manifest page in Slack API site. Replace the base URL _(`https://example.com` but keep the path `/slack/events`)._

  ```
  # Example
  ...
  request_url: https://4342423423.ngrok.io/slack/events
  ....OR
  request_url: https://super-app-name.fly.dev/slack/events
  ....
  ```

- After updating the URLs on the Slack API website, there will be a warning  `Click here to verify` - click it, and if your servers are running correctly, you'll get a success ✅ from Slack.
- (_Optional: Testing Webhooks_) [Handy tools to debug requests](https://webhook.site) as well as testing different HTTP responses [mock.codes](https://mock.codes/).

### 🎉 Use the app

🥂 You did it! Your `Workflow Buddy` is running locally and ready to interact with. Let's open App Home to see it working, open Workflow Builder, then try out a **Quickstart** to get your feet wet.

- 🏠 Open the Worflow Buddy App Home by searching `@Workflow Buddy` in Slack and selecting the bot. You should see something like the following:

  ![Image of Workflow Buddy App Home](/assets/workflow-buddy-app-home-orange-bg-sm.png)

- 🛠Take a look around, and now you'll want to open Slack Workflow Builder.  Up by the ✍ `New message` icon you can click your Workspace name and a drop down menu will appear. `<Workspace Name>`-> `Tools` -> `Workflow Builder`. It will open in a new window.
- 👩‍🏫 Now that you have everything open, let's learn how to **[create a simple Workflow (Beginner Quickstart)](#beginner-quickstart-create-a-simple-workflow)!**

---

## Development

If you're interested in contributing to Workflow Buddy through code.

### UI/UX Development

For the "UI" block surfaces (especially App Home), highly recommend opening in [Block Kit Builder](https://app.slack.com/block-kit-builder/) with the helper utility `get_block_kit_builder_link()`.

```
# Open Python REPL
>>> import utils
>>> utils.get_block_kit_builder_link(view=utils.build_app_home_view())
# copy the resulting link into address bar, avoiding the '' Python surrounds it with.
```

### How it works

For Slack events, this app basically just acts as a proxy. As long as the event is added to the bot's OAuth scopes, it should be able to proxy it through to your **Workflow Builder** flow.

For the new actions, it registers a **Workflow Builder Step** - unfortunately each app is limited to 10 registered with Slack. To get around that limitation, we have the user select from a static select list of actions that have been implemented on the server, then update the modal to give them the appropriate options. For example, if the user wants to `Send a webhook`, we'll then update the modal to have an input for the Webhook URL, and a text box for the body they want to send.

**Data**: Config data (basically just webhooks for now) is persisted on disk using Using a very simple cache + JSON file to persist webhook config data - it's not very robust, so highly recommend keeping a copy of the JSON file as backup to easily import if config is destroyed.

### Where is the configuration data store?

It's using a very simple cache + JSON file to persist webhook config data - it's not very robust, so **highly recommend** using the `Export` function to save a backup to easily `Import` if config is destroyed.

Depending on your deployment options, you may need to take extra steps to persist the local file data until a more persistent data store is added.


### Tools

We use a number of tools in & around this repo to improve the code quality:

- Black formatter
- [Sourcery.ai - improved code suggestions for Python](https://docs.sourcery.ai/Welcome/)

---
