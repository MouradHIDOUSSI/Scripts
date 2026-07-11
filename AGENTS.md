# AGENTS.md

## Commands

```powershell
# Run a script
python hello.py --name "Alice"

# CSR 1000V automation agent
python router_agent.py --host <ip> --username admin --password cisco <action> [args]

# Available actions:
#   show <command>       — run any show command
#   config <cmd>...      — send config commands
#   facts                — device facts (version, serial)
#   health               — quick CPU / memory / interfaces
#   backup               — save running-config to backups/
#   diff <baseline>      — diff running-config vs a file
#   audit                — security & compliance scan
#   troubleshoot         — collect full device bundle to troubleshoot/
#   ping <target>        — ping from the router
#   traceroute <target>  — traceroute from the router
#   apply-config <file>  — push config lines from a text file
#   save                 — write memory
#   deploy-vlan <id> <name>
#   watch <cmd> --interval 5  — poll periodically (Ctrl+C to stop)

# Run all tests
python -m pytest tests/ -v

# Run a single test
python -m pytest tests/test_router_agent.py::test_audit_help -v
```

## Structure

- `router_agent.py` — CSR 1000V agent (SSH via netmiko), supports 14 subcommands
- `tests/` — pytest tests, one file per script (`test_<name>.py`)
- `requirements.txt` — dependencies

## Conventions

- Scripts use `argparse` for CLI args
- Tests run scripts via `subprocess.run` using `cwd=Path(__file__).resolve().parent.parent`
- All router_agent subcommands have a corresponding `test_<name>_help` unit test
