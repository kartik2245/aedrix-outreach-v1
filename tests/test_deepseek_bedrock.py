"""
tests/test_deepseek_bedrock.py
Optional standalone test runner wrapper for tests suite.
"""

def test_deepseek_bedrock_standalone_runner():
    """Verify standalone script test_deepseek_bedrock.py exists in project root."""
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(base_dir, "test_deepseek_bedrock.py")
    assert os.path.exists(script_path)