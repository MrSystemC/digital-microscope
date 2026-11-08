"""Basic smoke tests for Digital Microscope."""
import json
from microscope.core import DigitalMicroscope

def test_json():
    m = DigitalMicroscope()
    root = m.analyze('{"a": 1, "b": [2, 3]}', "t.json")
    assert root.metadata["detected_type"] == "json"
    stats = m.get_stats(root)
    assert stats["total_molecules"] > 3

def test_python():
    m = DigitalMicroscope()
    code = "def foo():\n    return 42\n"
    root = m.analyze(code, "t.py")
    assert root.metadata["detected_type"] == "python"
    assert any(c.type == "functions" for c in root.children)

def test_text():
    m = DigitalMicroscope()
    root = m.analyze("Hello world. This is a test.", "t.txt")
    assert root.metadata["detected_type"] == "text"
    assert root.metadata["word_count"] >= 5

if __name__ == "__main__":
    test_json()
    test_python()
    test_text()
    print("All tests passed")
