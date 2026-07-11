import argparse
import json
import os
import re
import time
from datetime import datetime
from difflib import unified_diff
from pathlib import Path
from typing import Optional

from netmiko import ConnectHandler


def connect(host: str, username: str, password: str, port: int = 22, secret: Optional[str] = None):
    device = {
        "device_type": "cisco_ios",
        "host": host,
        "username": username,
        "password": password,
        "port": port,
        "secret": secret or password,
    }
    return ConnectHandler(**device)


def show(conn, command: str) -> str:
    return conn.send_command(command)


def config(conn, commands: list[str]) -> str:
    return conn.send_config_set(commands)


# ── Backup ────────────────────────────────────────────────────────────────

def cmd_backup(conn, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    hostname = show(conn, "show running-config | include hostname").strip()
    name = hostname.replace("hostname ", "").strip() if hostname else "router"
    path = os.path.join(output_dir, f"{name}_{ts}.cfg")
    config_text = conn.send_command("show running-config")
    with open(path, "w") as f:
        f.write(config_text)
    print(f"Backup saved to {path}")
    return path


# ── Diff ──────────────────────────────────────────────────────────────────

def cmd_diff(conn, baseline_path: str):
    if not os.path.exists(baseline_path):
        print(f"Baseline file not found: {baseline_path}")
        return
    with open(baseline_path) as f:
        baseline = f.readlines()
    current = conn.send_command("show running-config").splitlines(keepends=True)
    diff = unified_diff(baseline, current, fromfile="baseline", tofile="current")
    print("".join(diff))


# ── Audit ─────────────────────────────────────────────────────────────────

def cmd_audit(conn):
    issues = []

    interfaces = show(conn, "show ip interface brief")
    down = re.findall(r"(\S+)\s+down\s+down", interfaces)
    for intf in down:
        issues.append(f"Interface {intf} is down/down")

    acl_check = show(conn, "show running-config | include ip access-group")
    if not acl_check.strip():
        issues.append("No ACLs applied to any interface")

    users = show(conn, "show running-config | include username")
    weak = re.findall(r"username\s+(\S+)\s+password\s+0\s+(\S+)", users)
    for user, pw in weak:
        if len(pw) < 8:
            issues.append(f"User {user} has a short password ({len(pw)} chars)")

    banners = show(conn, "show running-config | include banner")
    if not banners.strip():
        issues.append("No login banner configured")

    logging = show(conn, "show running-config | include logging host")
    if not logging.strip():
        issues.append("No remote syslog server configured")

    ntp = show(conn, "show running-config | include ntp server")
    if not ntp.strip():
        issues.append("No NTP server configured")

    if not issues:
        print("No issues found.")
    else:
        print(f"Found {len(issues)} issue(s):")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")


# ── Troubleshoot ──────────────────────────────────────────────────────────

def cmd_troubleshoot(conn, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"troubleshoot_{ts}.txt")

    commands = [
        ("show version", "VERSION"),
        ("show running-config", "RUNNING-CONFIG"),
        ("show startup-config", "STARTUP-CONFIG"),
        ("show ip interface brief", "INTERFACES"),
        ("show ip route", "ROUTING-TABLE"),
        ("show interfaces", "INTERFACE-DETAIL"),
        ("show vlan brief", "VLANS"),
        ("show log", "LOGS"),
        ("show processes cpu", "CPU"),
        ("show memory statistics", "MEMORY"),
        ("show ip ospf neighbor", "OSPF-NEIGHBORS"),
        ("show ip bgp summary", "BGP-SUMMARY"),
    ]

    with open(path, "w") as f:
        for cmd, label in commands:
            f.write(f"\n{'='*60}\n")
            f.write(f"  {label}\n")
            f.write(f"{'='*60}\n")
            try:
                output = show(conn, cmd)
                f.write(output + "\n")
            except Exception as e:
                f.write(f"Error: {e}\n")

    print(f"Troubleshooting bundle saved to {path}")
    return path


# ── Ping ──────────────────────────────────────────────────────────────────

def cmd_ping(conn, target: str, count: int = 5):
    output = conn.send_command(f"ping {target} repeat {count}")
    print(output)


# ── Traceroute ────────────────────────────────────────────────────────────

def cmd_traceroute(conn, target: str):
    output = conn.send_command(f"traceroute {target}")
    print(output)


# ── Apply config from file ────────────────────────────────────────────────

def cmd_apply_config(conn, file_path: str):
    if not os.path.exists(file_path):
        print(f"Config file not found: {file_path}")
        return
    with open(file_path) as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("!")]
    output = config(conn, lines)
    print(output)


# ── Save ──────────────────────────────────────────────────────────────────

def cmd_save(conn):
    output = conn.save_config()
    print("Configuration saved to startup-config" if output is None else output)


# ── Deploy VLAN ───────────────────────────────────────────────────────────

def cmd_deploy_vlan(conn, vlan_id: int, name: str):
    cmds = [
        f"vlan {vlan_id}",
        f"name {name}",
        "end",
    ]
    output = config(conn, cmds)
    print(output)


# ── Watch / Monitor ───────────────────────────────────────────────────────

def cmd_watch(conn, command: str, interval: int):
    try:
        while True:
            ts = datetime.now().strftime("%H:%M:%S")
            output = show(conn, command).strip()
            print(f"[{ts}] $ {command}")
            print(output)
            print("-" * 40)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Monitoring stopped.")


# ── Main dispatch ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cisco CSR 1000V AI Agent")
    parser.add_argument("--host", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--secret", help="Enable password (defaults to --password)")

    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("show").add_argument("command")
    sub.add_parser("config").add_argument("commands", nargs="+")
    sub.add_parser("facts")
    sub.add_parser("health")

    sub.add_parser("backup").add_argument("--output-dir", default="backups")
    sub.add_parser("diff").add_argument("baseline")
    sub.add_parser("audit")
    sub.add_parser("troubleshoot").add_argument("--output-dir", default="troubleshoot")
    sub.add_parser("ping").add_argument("target")
    sub.add_parser("traceroute").add_argument("target")
    sub.add_parser("apply-config").add_argument("file")
    sub.add_parser("save")
    deploy_p = sub.add_parser("deploy-vlan")
    deploy_p.add_argument("vlan_id", type=int)
    deploy_p.add_argument("name")
    watch_p = sub.add_parser("watch")
    watch_p.add_argument("command")
    watch_p.add_argument("--interval", type=int, default=5)

    args = parser.parse_args()

    conn = connect(args.host, args.username, args.password, args.port, args.secret)
    conn.enable()

    if args.action == "show":
        print(show(conn, args.command))

    elif args.action == "config":
        print(config(conn, args.commands))

    elif args.action == "facts":
        facts = conn.send_command("show version", use_textfsm=True)
        print(json.dumps(facts if isinstance(facts, dict) else facts[0], indent=2))

    elif args.action == "health":
        print("=== Interfaces ===")
        print(show(conn, "show ip interface brief"))
        print("\n=== CPU ===")
        print(show(conn, "show processes cpu | include CPU utilization"))
        print("\n=== Memory ===")
        print(show(conn, "show memory statistics | include Processor"))

    elif args.action == "backup":
        cmd_backup(conn, args.output_dir)

    elif args.action == "diff":
        cmd_diff(conn, args.baseline)

    elif args.action == "audit":
        cmd_audit(conn)

    elif args.action == "troubleshoot":
        cmd_troubleshoot(conn, args.output_dir)

    elif args.action == "ping":
        cmd_ping(conn, args.target)

    elif args.action == "traceroute":
        cmd_traceroute(conn, args.target)

    elif args.action == "apply-config":
        cmd_apply_config(conn, args.file)

    elif args.action == "save":
        cmd_save(conn)

    elif args.action == "deploy-vlan":
        cmd_deploy_vlan(conn, args.vlan_id, args.name)

    elif args.action == "watch":
        cmd_watch(conn, args.command, args.interval)

    conn.disconnect()


if __name__ == "__main__":
    main()
