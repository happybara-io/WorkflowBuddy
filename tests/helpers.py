def check_lists_equal(L1, L2):
    is_equal = len(L1) == len(L2) and sorted(L1) == sorted(L2)
    if not is_equal:
        raise AssertionError(f"Lists are not equal! {L1} vs {L2}")
