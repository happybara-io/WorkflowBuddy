# test_constants, renamed to avoid issues with imports as `constants` or run as a test file as `test_constants` by pytest.

# some pulled from Slack API examples, others direct from testing
SLACK_DEMO_EVENTS = {
    "app_mention": {
        "type": "app_mention",
        "user": "U061F7AUR",
        "text": "<@U0LAN0Z89> is it everything a river should be?",
        "ts": "1515449522.000016",
        "channel": "C0LAN2Q65",
        "event_ts": "1515449522000016",
    },
    "channel_created": {
        "type": "channel_created",
        "channel": {
            "id": "C04659N6J0G",
            "is_channel": True,
            "name": "workflow-channel-created",
            "name_normalized": "workflow-channel-created",
            "created": 1665073074,
            "creator": "UMTUPT124",
            "is_shared": False,
            "is_org_shared": False,
            "context_team_id": "TKM6AU1FG",
        },
        "event_ts": "1665073075.112600",
    },
    "reaction_added": {
        "type": "reaction_added",
        "user": "U024BE7LH",
        "reaction": "thumbsup",
        "item_user": "U0G9QF9C6",
        "item": {"type": "message", "channel": "C0G9QF9GZ", "ts": "1360782400.498405"},
        "event_ts": "1360782804.083113",
    },
}
