import buddy.step_actions as sut
import buddy.errors
import pytest


def test_run_random_int():
    lower = 0
    upper = 100
    test_step = {
        "inputs": {"lower_bound": {"value": "0"}, "upper_bound": {"value": "100"}}
    }
    out = sut.run_random_int(test_step)
    random_int_text = out["random_int_text"]
    assert type(random_int_text) is str
    assert int(random_int_text) >= lower and int(random_int_text) <= upper
