from slurm_usage_history.tools import unpack_nodelist_string


def test_unpack_nodelist_with_range():
    """Test unpacking node list with range notation."""
    result = unpack_nodelist_string("gpu[08-09,11,14]")
    assert result == ["gpu08", "gpu09", "gpu11", "gpu14"]


def test_unpack_nodelist_with_single_digit():
    """Test that single digit nodes without padding stay unpadded."""
    result = unpack_nodelist_string("gpu[5,6,7]")
    assert result == ["gpu5", "gpu6", "gpu7"]


def test_unpack_nodelist_with_two_digit():
    """Test that two digit nodes remain properly formatted."""
    result = unpack_nodelist_string("gpu[30,31,32]")
    assert result == ["gpu30", "gpu31", "gpu32"]


def test_unpack_nodelist_mixed():
    """Test mixed single and double digit nodes - no padding."""
    result = unpack_nodelist_string("gpu[5,10,30]")
    assert result == ["gpu5", "gpu10", "gpu30"]


def test_unpack_nodelist_single_node():
    """Test single node without brackets."""
    result = unpack_nodelist_string("gpu16")
    assert result == ["gpu16"]


def test_unpack_nodelist_none():
    """Test handling of None or empty input."""
    result = unpack_nodelist_string(None)
    assert result == []

    result = unpack_nodelist_string("None assigned")
    assert result == []


def test_unpack_nodelist_with_range_and_singles():
    """Test combination of ranges and single values - no padding."""
    result = unpack_nodelist_string("gpu[5-7,10,30-32]")
    assert result == ["gpu5", "gpu6", "gpu7", "gpu10", "gpu30", "gpu31", "gpu32"]


def test_unpack_nodelist_comma_separated_simple():
    """Test comma-separated simple node names without brackets."""
    result = unpack_nodelist_string("gpu05,gpu06,gpu07")
    assert result == ["gpu05", "gpu06", "gpu07"]


def test_unpack_nodelist_malformed_incomplete_bracket():
    """Test malformed node names with incomplete brackets like 'gpu[30'."""
    result = unpack_nodelist_string("gpu[30")
    assert result == ["gpu30"]

    result = unpack_nodelist_string("gpu[05")
    assert result == ["gpu05"]


def test_unpack_nodelist_malformed_numbers_only():
    """Test malformed strings that are just numbers and brackets like '14-15]'."""
    result = unpack_nodelist_string("14-15]")
    assert result == []

    result = unpack_nodelist_string("[30]")
    assert result == []


def test_unpack_nodelist_range_notation():
    """Test range notation like 'node[06-08]'."""
    result = unpack_nodelist_string("node[06-08]")
    assert result == ["node06", "node07", "node08"]


def test_unpack_nodelist_list_notation():
    """Test list notation like 'node[01,11]'."""
    result = unpack_nodelist_string("node[01,11]")
    assert result == ["node01", "node11"]


def test_unpack_nodelist_mixed_notation():
    """Test mixed notation like 'gpu[06-08,10,15-16]'."""
    result = unpack_nodelist_string("gpu[06-08,10,15-16]")
    assert result == ["gpu06", "gpu07", "gpu08", "gpu10", "gpu15", "gpu16"]


def test_unpack_nodelist_single_digit_range():
    """Test single digit range like 'node[1-5]' - no padding."""
    result = unpack_nodelist_string("node[1-5]")
    assert result == ["node1", "node2", "node3", "node4", "node5"]


def test_unpack_nodelist_complex_mixed():
    """Test complex mixed notation like 'node[1,4-5,9]' - no padding."""
    result = unpack_nodelist_string("node[1,4-5,9]")
    assert result == ["node1", "node4", "node5", "node9"]


def test_unpack_nodelist_zero_padded_range():
    """Test zero-padded range like 'node[01-05]' - preserves padding."""
    result = unpack_nodelist_string("node[01-05]")
    assert result == ["node01", "node02", "node03", "node04", "node05"]
