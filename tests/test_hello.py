import subprocess
import sys
from pathlib import Path


def test_hello_default():
    result = subprocess.run(
        [sys.executable, str(Path("hello.py"))],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert result.stdout.strip() == "Hello, World!"


def test_hello_custom_name():
    result = subprocess.run(
        [sys.executable, str(Path("hello.py")), "--name", "OpenCode"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert result.stdout.strip() == "Hello, OpenCode!"
