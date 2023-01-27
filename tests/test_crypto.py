import buddy.crypto as sut
from slack_sdk.oauth.installation_store import Installation
from cryptography.fernet import Fernet

test_secret_key = Fernet.generate_key()
secret_str = "xoxb-abcfdfdf-13243434-34343434343"


def test_encrypt_and_decrypt():

    encrypted_str = sut.encrypt_string(test_secret_key, secret_str)
    assert secret_str not in encrypted_str
    print("encrypted", encrypted_str)
    decrypted = sut.decrypt_data(test_secret_key, encrypted_str)
    print("decrypted", decrypted)
    assert secret_str == decrypted


def test_encrypt_and_decrypt_slack_installation_fields():
    init_team_name = "My Private Slack Workspace"
    init_bot_token = "xoxb-111"
    init_bot_refresh_token = "11111111111111111"
    init_user_token = "xoxp-111"
    init_user_refresh_token = "222222222222222"

    installation = Installation(
        app_id="A111",
        enterprise_id="E111",
        team_id="T111",
        team_name=init_team_name,
        user_id="U111",
        bot_id="B111",
        bot_token=init_bot_token,
        bot_refresh_token=init_bot_refresh_token,
        bot_scopes=["chat:write"],
        bot_user_id="U222",
        user_token=init_user_token,
        user_refresh_token=init_user_refresh_token,
    )
    sut.encrypt_slack_fields(test_secret_key, installation)

    assert init_team_name != installation.team_name
    assert init_bot_token != installation.bot_token
    assert init_bot_refresh_token != installation.bot_refresh_token
    assert init_user_token != installation.user_token
    assert init_user_refresh_token != installation.user_refresh_token

    sut.decrypt_slack_fields(test_secret_key, installation)

    assert init_team_name == installation.team_name
    assert init_bot_token == installation.bot_token
    assert init_bot_refresh_token == installation.bot_refresh_token
    assert init_user_token == installation.user_token
    assert init_user_refresh_token == installation.user_refresh_token
