#######################
# Tooling to use when writing or during tests.
# Anything that helps with validation :D
#######################


def oasd(obj):
    """
    Get all of an object's properties as a dict.
    """
    return dict(
        (key, value)
        for key, value in obj.__dict__.items()
        if not callable(value) and not key.startswith("__")
    )
