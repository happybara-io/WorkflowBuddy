class WorkflowBuddyError(Exception):
    """Base class for all Workflow Buddy errors"""

    pass


class WorkflowStepFailError(WorkflowBuddyError):
    """Used to indicate a step should be ended with `fail()`. Error exists to let us nest
    error handling logic in small functions while still easily handling failure cases.

    Attributes:
        errmsg (str): The message to display to users of Workflow Builder detailing why a failure occurred.
    """

    def __init__(self, errmsg):
        self.errmsg = errmsg
