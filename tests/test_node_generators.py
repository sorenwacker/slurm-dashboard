import pandas as pd
from backend.app.services.charts.node_generators import generate_node_usage


def test_node_names_preserved():
    """Test that node names are preserved exactly as they appear in data."""
    df = pd.DataFrame({
        "NodeList": [["gpu5"], ["gpu30"], ["gpu05"], ["gpu10"]],
        "CPUHours": [10.0, 20.0, 15.0, 25.0],
        "GPUHours": [5.0, 10.0, 8.0, 12.0],
    })

    result = generate_node_usage(df)

    cpu_nodes = result["cpu_usage"]["x"]
    gpu_nodes = result["gpu_usage"]["x"]

    # Node names should be preserved exactly as they are in the data
    assert "gpu5" in cpu_nodes
    assert "gpu30" in cpu_nodes
    assert "gpu05" in cpu_nodes
    assert "gpu10" in cpu_nodes

    assert "gpu5" in gpu_nodes
    assert "gpu30" in gpu_nodes
    assert "gpu05" in gpu_nodes
    assert "gpu10" in gpu_nodes


def test_node_list_expansion():
    """Test that pre-expanded node lists work correctly."""
    df = pd.DataFrame({
        "NodeList": [["gpu05", "gpu06"], ["gpu30", "gpu31", "gpu32"]],
        "CPUHours": [10.0, 30.0],
        "GPUHours": [5.0, 15.0],
    })

    result = generate_node_usage(df)

    cpu_nodes = result["cpu_usage"]["x"]

    # Check that all nodes are preserved
    assert "gpu05" in cpu_nodes
    assert "gpu06" in cpu_nodes
    assert "gpu30" in cpu_nodes
    assert "gpu31" in cpu_nodes
    assert "gpu32" in cpu_nodes


def test_simple_node_names():
    """Test simple node names."""
    df = pd.DataFrame({
        "NodeList": [["node1"], ["node2"]],
        "CPUHours": [10.0, 20.0],
        "GPUHours": [5.0, 10.0],
    })

    result = generate_node_usage(df)

    cpu_nodes = result["cpu_usage"]["x"]

    assert "node1" in cpu_nodes
    assert "node2" in cpu_nodes


def test_empty_nodelist():
    """Test handling of empty NodeList."""
    df = pd.DataFrame({
        "CPUHours": [10.0],
        "GPUHours": [5.0],
    })

    result = generate_node_usage(df)

    assert result["cpu_usage"]["x"] == []
    assert result["gpu_usage"]["x"] == []


def test_already_expanded_nodes():
    """Test that pre-expanded node lists (from data ingestion) work correctly."""
    # This mimics what the data looks like after ingestion - already expanded
    df = pd.DataFrame({
        "NodeList": [["gpu06", "gpu07", "gpu08", "gpu10"], ["gpu30", "gpu31"]],
        "CPUHours": [40.0, 20.0],
        "GPUHours": [20.0, 10.0],
    })

    result = generate_node_usage(df)

    cpu_nodes = result["cpu_usage"]["x"]

    # Should have all expanded nodes
    assert "gpu06" in cpu_nodes
    assert "gpu07" in cpu_nodes
    assert "gpu08" in cpu_nodes
    assert "gpu10" in cpu_nodes
    assert "gpu30" in cpu_nodes
    assert "gpu31" in cpu_nodes

    # Should not have any brackets in node names
    for node in cpu_nodes:
        assert "[" not in node
        assert "]" not in node


def test_compressed_notation_in_dashboard():
    """Test dashboard handling of compressed SLURM notation from legacy data."""
    # This mimics legacy data that has unexpanded compressed notation
    df = pd.DataFrame({
        "NodeList": ["gpu[01-03,05]", "influ[1-2]"],
        "CPUHours": [40.0, 20.0],
        "GPUHours": [20.0, 10.0],
    })

    result = generate_node_usage(df)

    cpu_nodes = result["cpu_usage"]["x"]

    # Should expand compressed notation
    assert "gpu01" in cpu_nodes
    assert "gpu02" in cpu_nodes
    assert "gpu03" in cpu_nodes
    assert "gpu05" in cpu_nodes
    assert "influ1" in cpu_nodes
    assert "influ2" in cpu_nodes

    # Should not have any brackets in final node names
    for node in cpu_nodes:
        assert "[" not in node
        assert "]" not in node
