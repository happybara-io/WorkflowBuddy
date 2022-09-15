## Act as our datastore until it's worth adding - ope, jk webhooks should be confidential though 🤦

# TODO: these webhook URLs should only ever be committed if it's a private repo - even then questionable
# EVENT_WORKFLOW_MAP = {
#     'channel_joined': [],
#     'app_mention': [
#         {
#             'webhook_url': ''
#         }
#     ]
# }

EVENT_APP_MENTION = "app_mention"
EVENT_CHANNEL_CREATED = "channel_created"