# App Mention Trigger with (almost) all action steps

This is a quick demo showcasing the core concepts of using Workflow Buddy.

- _Prep done before the video (if you are trying to replicate):_
  - _Creating Slack app & deploying Workflow Buddy._
  - _Creating the Workflow from the template `app_mention_and_e2e_test.slackworkflow`. This outputs the Webhook URL._
  - _Using the `Add` button in the App Home to set up connection between `app_mention` and Webhook URL._
- **👀 What you'll see:**
  - Quick run through of all the different steps populated in the workflow (only one missing is `Create a channel`), since we run this workflow a lot :D 
  - Triggering Workflow with Slack event `app_mention`, which is not available in the default Workflow Builder.
  - The `Wait for approval` step in action
  - A final message showcasing all of the outputs and actions that occurred, sent to the person who triggered workflow (in this case, me!).

---

https://user-images.githubusercontent.com/8552248/194412612-61697aac-18e1-4572-84d9-e1b86de2657e.mp4

