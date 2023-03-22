#######################
# Tooling to use when writing or during tests.
# Anything that helps with validation :D
#######################
from typing import Dict, Any


def oasd(obj) -> Dict[str, Any]:
    """
    Get all of an object's properties as a dict.
    """
    return dict(
        (key, value)
        for key, value in obj.__dict__.items()
        if not callable(value) and not key.startswith("__")
    )


def print_oauth_tables(engine) -> None:
    with engine.connect() as con:
        rs = con.execute("SELECT * FROM slack_bots")
        for row in rs:
            print(row)
        print("========")
        rs = con.execute("SELECT * FROM slack_installations")
        for row in rs:
            print(row)
