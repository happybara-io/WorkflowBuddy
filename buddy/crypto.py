# abstraction for whatever crypto library we end up using for encryption-at-rest.
# Application-level encryption adds a layer of security.
from slack_sdk.oauth.installation_store.models.bot import Bot
from slack_sdk.oauth.installation_store.models.installation import Installation
from cryptography.fernet import Fernet, MultiFernet

from typing import Union
from buddy.constants import UTF8


# TODO: how might i easily add to this list of fields, without
# causing issue for data that has already been stored unencrypted?
# how can I detect if a value I pulled from DB was already encrypted,
# because I want to avoid accidentally double-encrypting items.
SLACK_SENSITIVE_FIELDS = [
    "team_name",
    "bot_token",
    "bot_refresh_token",
    "user_token",
    "user_refresh_token",
]


def encrypt_string(secret_key: str, plain_text_data: str) -> str:
    fkey = Fernet(secret_key)
    mf = MultiFernet([fkey])
    token: bytes = mf.encrypt(plain_text_data.encode(encoding=UTF8))
    return token.decode(encoding=UTF8)


def decrypt_data(secret_key: str, encrypted_token: str) -> str:
    fkey = Fernet(secret_key)
    mf = MultiFernet([fkey])
    decrypted_token = mf.decrypt(encrypted_token)
    return decrypted_token.decode(encoding=UTF8)


def encrypt_slack_fields(
    encryption_key: str, slack_oauth_data: Union[Installation, Bot]
) -> None:
    """
    Encrypting only certain dangerous or identifying fields provided by Slack OAuth process.
    team_name: even knowing name is too much info for an attacker to have.
    tokens(and refresh): these need to be encrypted, since they are what allows us to change
        workspaces.
    """
    for field in SLACK_SENSITIVE_FIELDS:
        try:
            val = getattr(slack_oauth_data, field)
        except AttributeError:
            continue
        if val is not None:
            val = encrypt_string(encryption_key, val)
        setattr(slack_oauth_data, field, val)


def decrypt_slack_fields(
    encryption_key: str, slack_oauth_data: Union[Installation, Bot]
) -> None:
    for field in SLACK_SENSITIVE_FIELDS:
        try:
            val = getattr(slack_oauth_data, field)
        except AttributeError:
            continue
        if val is not None:
            val = decrypt_data(encryption_key, val)
        setattr(slack_oauth_data, field, val)
