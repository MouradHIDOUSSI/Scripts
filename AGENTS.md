# AGENTS.md

## Commands

```powershell
# Run a script
python hello.py --name "Alice"

# Run all tests
python -m pytest tests/ -v

# Run a single test
python -m pytest tests/test_hello.py::test_hello_custom_name -v
```

## Structure

- Project root contains standalone Python scripts (`if __name__ == "__main__"` entrypoints)
- `tests/` — pytest tests, one file per script (`test_<name>.py`)
- `requirements.txt` — dependencies

## Conventions

- Scripts use `argparse` for CLI args
- Tests run scripts via `subprocess.run` using `cwd=Path(__file__).resolve().parent.parent`
