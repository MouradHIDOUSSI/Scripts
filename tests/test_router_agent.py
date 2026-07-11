import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = "router_agent.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_help():
    r = _run("--help")
    assert "Cisco CSR 1000V AI Agent" in r.stdout
    assert r.returncode == 0


def test_show_help():
    r = _run("show", "--help")
    assert r.returncode == 0


def test_config_help():
    r = _run("config", "--help")
    assert r.returncode == 0


def test_facts_help():
    r = _run("facts", "--help")
    assert r.returncode == 0


def test_health_help():
    r = _run("health", "--help")
    assert r.returncode == 0


def test_backup_help():
    r = _run("backup", "--help")
    assert "output-dir" in r.stdout
    assert r.returncode == 0


def test_diff_help():
    r = _run("diff", "--help")
    assert r.returncode == 0


def test_audit_help():
    r = _run("audit", "--help")
    assert r.returncode == 0


def test_troubleshoot_help():
    r = _run("troubleshoot", "--help")
    assert r.returncode == 0


def test_ping_help():
    r = _run("ping", "--help")
    assert r.returncode == 0


def test_traceroute_help():
    r = _run("traceroute", "--help")
    assert r.returncode == 0


def test_apply_config_help():
    r = _run("apply-config", "--help")
    assert r.returncode == 0


def test_save_help():
    r = _run("save", "--help")
    assert r.returncode == 0


def test_deploy_vlan_help():
    r = _run("deploy-vlan", "--help")
    assert r.returncode == 0


def test_watch_help():
    r = _run("watch", "--help")
    assert r.returncode == 0
