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

import router_config as rc


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
    output = config(conn, rc.vlan_cmds(vlan_id, name))
    print(output)


# ── Firmware upgrade ───────────────────────────────────────────────────────

def cmd_firmware_upgrade(conn, protocol, server, filename, username=None, password=None, verify_only=False, reload=False):
    if verify_only:
        dir_out = conn.send_command("dir bootflash:")
        print(dir_out)
        ver = conn.send_command("show version | include Version")
        print(ver)
        boot = conn.send_command("show boot")
        print(boot)
        return

    dest = f"bootflash:{filename}"

    if protocol == "tftp":
        copy_cmd = f"copy tftp://{server}/{filename} {dest}"
    elif protocol == "ftp":
        copy_cmd = f"copy ftp://{username}:{password}@{server}/{filename} {dest}"
    elif protocol == "scp":
        copy_cmd = f"copy scp://{username}@{server}/{filename} {dest}"
    else:
        print(f"Unsupported protocol: {protocol}")
        return

    print(f"Copying {filename} from {server} via {protocol.upper()}...")
    output = conn.send_command_timing(copy_cmd, strip_prompt=False, strip_command=False)
    if protocol == "scp" and username:
        output += conn.send_command_timing(password, strip_prompt=False, strip_command=False)
    print(output)

    verify = conn.send_command(f"verify /md5 bootflash:{filename}")
    print(f"Verification:\n{verify}")

    boot_set = [f"no boot system", f"boot system flash bootflash:{filename}"]
    config(conn, boot_set)
    conn.save_config()
    print(f"Boot variable set to {filename}")

    if reload:
        print("Reloading router in 3 minutes...")
        conn.send_command("reload in 3", expect_string=r"\[confirm\]")
        conn.send_command("y")
        print("Reload scheduled.")

    print(f"Firmware upgrade to {filename} staged. Use 'verify-only' to check status.")


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


# ── Configure dispatch ────────────────────────────────────────────────────

def cmd_configure(conn, args):
    if args.config_action == "system":
        cmds = rc.system_cmds(
            hostname=args.hostname,
            banner=args.banner,
            domain=args.domain,
            nameservers=args.nameservers,
            enable_secret=args.enable_secret,
        )

    elif args.config_action == "user":
        cmds = rc.user_cmds(args.username, args.password, args.privilege)

    elif args.config_action == "aaa":
        cmds = rc.aaa_cmds(args.auth_login, args.auth_enable)

    elif args.config_action == "ssh":
        cmds = rc.ssh_cmds(args.domain, args.rsa_bits)

    elif args.config_action == "interface":
        cmds = rc.interface_cmds(
            args.name,
            ip_address=args.ip,
            subnet_mask=args.mask,
            description=args.description,
            duplex=args.duplex,
            speed=args.speed,
            mtu=args.mtu,
            shutdown=args.shutdown,
            vrf=args.vrf,
        )

    elif args.config_action == "interface-vlan":
        cmds = rc.interface_vlan_cmds(
            args.vlan_id,
            ip_address=args.ip,
            subnet_mask=args.mask,
            description=args.description,
            shutdown=args.shutdown,
        )

    elif args.config_action == "vlan":
        cmds = rc.vlan_cmds(args.vlan_id, args.name)

    elif args.config_action == "trunk":
        cmds = rc.trunk_cmds(args.interface, args.allowed_vlans, args.native_vlan)

    elif args.config_action == "access-port":
        cmds = rc.access_port_cmds(args.interface, args.vlan_id)

    elif args.config_action == "port-security":
        cmds = rc.port_security_cmds(args.interface, args.max_mac, args.violation)

    elif args.config_action == "spanning-tree":
        cmds = rc.spanning_tree_cmds(args.mode)

    elif args.config_action == "static-route":
        cmds = rc.static_route_cmds(args.network, args.mask, args.next_hop, args.distance, args.vrf)

    elif args.config_action == "ospf":
        networks = list(zip(args.networks[::2], args.networks[1::2]))
        cmds = rc.ospf_cmds(args.process, args.router_id, networks, args.area, args.interfaces)

    elif args.config_action == "eigrp":
        networks = list(zip(args.networks[::2], args.networks[1::2]))
        cmds = rc.eigrp_cmds(args.as_number, args.router_id, networks, args.interfaces)

    elif args.config_action == "bgp":
        nets = list(zip(args.networks[::2], args.networks[1::2]))
        neighbors = list(zip(args.neighbors[::2], args.neighbors[1::2]))
        cmds = rc.bgp_cmds(args.as_number, args.router_id, nets, neighbors, args.redistribute_connected)

    elif args.config_action == "acl-standard":
        entries = list(zip(args.permit, args.networks, args.wildcards))
        cmds = rc.acl_standard_cmds(args.acl_id, entries)

    elif args.config_action == "acl-extended":
        entries = list(zip(args.permit, args.protos, args.srcs, args.src_wilds, args.dsts, args.dst_wilds, args.eq))
        cmds = rc.acl_extended_cmds(args.acl_id, entries)

    elif args.config_action == "acl-apply":
        cmds = rc.acl_apply_cmds(args.interface, args.acl_id, args.direction)

    elif args.config_action == "nat-static":
        cmds = rc.nat_static_cmds(args.inside_local, args.inside_global, args.interface)

    elif args.config_action == "nat-dynamic":
        cmds = rc.nat_dynamic_cmds(args.acl_id, args.pool, args.start_ip, args.end_ip, args.mask, args.overload)

    elif args.config_action == "nat-overload":
        cmds = rc.nat_interface_overload_cmds(args.acl_id, args.interface)

    elif args.config_action == "nat-interface":
        cmds = rc.nat_inside_outside_cmds(args.inside, args.outside)

    elif args.config_action == "dhcp-pool":
        cmds = rc.dhcp_pool_cmds(args.pool, args.network, args.mask, args.default_router, args.dns_servers, args.lease)

    elif args.config_action == "dhcp-exclude":
        cmds = rc.dhcp_exclude_cmds(args.start_ip, args.end_ip)

    elif args.config_action == "hsrp":
        cmds = rc.hsrp_cmds(args.interface, args.group, args.virtual_ip, args.priority, not args.no_preempt)

    elif args.config_action == "snmp":
        cmds = rc.snmp_cmds(args.community, args.location, args.contact, args.acl_id, args.trap_host)

    elif args.config_action == "logging":
        cmds = rc.logging_cmds(args.host, args.trap_level)

    elif args.config_action == "ntp":
        cmds = rc.ntp_cmds(args.server, args.prefer, args.source_interface)

    elif args.config_action == "qos":
        cmds = rc.qos_cmds(args.class_name, args.match_acl, args.bandwidth, args.priority, args.queue_limit, args.policy_name, args.interface)

    elif args.config_action == "crypto-ike":
        cmds = rc.crypto_ike_cmds(args.priority, args.encryption, args.hash, args.dh_group, args.lifetime)

    elif args.config_action == "crypto-ipsec":
        cmds = rc.crypto_ipsec_cmds(args.transform, args.esp_encryption, args.esp_auth)

    elif args.config_action == "crypto-map":
        cmds = rc.crypto_map_cmds(args.map_name, args.seq, args.peer, args.transform_set, args.acl_id, args.local_address, args.psk)

    elif args.config_action == "crypto-map-apply":
        cmds = rc.crypto_map_apply_cmds(args.interface, args.map_name)

    else:
        print(f"Unknown configuration action: {args.config_action}")
        return

    if cmds:
        output = config(conn, cmds)
        print(output)
    else:
        print("No commands generated.")


# ── Build configure subparser ─────────────────────────────────────────────

def build_configure_parser(sub):
    c = sub.add_parser("configure", help="Configure the router by category")

    csub = c.add_subparsers(dest="config_action", required=True)

    # system
    p = csub.add_parser("system")
    p.add_argument("--hostname")
    p.add_argument("--banner")
    p.add_argument("--domain")
    p.add_argument("--nameservers", nargs="*")
    p.add_argument("--enable-secret")

    # user
    p = csub.add_parser("user")
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--privilege", type=int, default=15)

    # aaa
    p = csub.add_parser("aaa")
    p.add_argument("--auth-login", default="default")
    p.add_argument("--auth-enable", default="default")

    # ssh
    p = csub.add_parser("ssh")
    p.add_argument("--domain", required=True)
    p.add_argument("--rsa-bits", type=int, default=2048)

    # interface
    p = csub.add_parser("interface")
    p.add_argument("--name", required=True)
    p.add_argument("--ip")
    p.add_argument("--mask")
    p.add_argument("--description")
    p.add_argument("--duplex", choices=["auto", "half", "full"])
    p.add_argument("--speed", choices=["10", "100", "1000", "10000", "auto"])
    p.add_argument("--mtu", type=int)
    p.add_argument("--shutdown", type=str, choices=["true", "false"], help="true=shutdown, false=no shutdown")
    p.add_argument("--vrf")

    # interface-vlan
    p = csub.add_parser("interface-vlan")
    p.add_argument("--vlan-id", type=int, required=True)
    p.add_argument("--ip")
    p.add_argument("--mask")
    p.add_argument("--description")
    p.add_argument("--shutdown", type=str, choices=["true", "false"])

    # vlan
    p = csub.add_parser("vlan")
    p.add_argument("--vlan-id", type=int, required=True)
    p.add_argument("--name")

    # trunk
    p = csub.add_parser("trunk")
    p.add_argument("--interface", required=True)
    p.add_argument("--allowed-vlans", default="all")
    p.add_argument("--native-vlan", type=int)

    # access-port
    p = csub.add_parser("access-port")
    p.add_argument("--interface", required=True)
    p.add_argument("--vlan-id", type=int, required=True)

    # port-security
    p = csub.add_parser("port-security")
    p.add_argument("--interface", required=True)
    p.add_argument("--max-mac", type=int, default=1)
    p.add_argument("--violation", choices=["protect", "restrict", "shutdown"], default="shutdown")

    # spanning-tree
    p = csub.add_parser("spanning-tree")
    p.add_argument("--mode", default="rapid-pvst", choices=["pvst", "rapid-pvst", "mst"])

    # static-route
    p = csub.add_parser("static-route")
    p.add_argument("--network", required=True)
    p.add_argument("--mask", required=True)
    p.add_argument("--next-hop", required=True)
    p.add_argument("--distance", type=int)
    p.add_argument("--vrf")

    # ospf
    p = csub.add_parser("ospf")
    p.add_argument("--process", type=int, required=True)
    p.add_argument("--router-id", required=True)
    p.add_argument("--networks", nargs="+", required=True, help="network wildcard pairs: 10.0.0.0 0.0.0.255 192.168.1.0 0.0.0.255")
    p.add_argument("--area", type=int, default=0)
    p.add_argument("--interfaces", nargs="*", help="OSPF-enabled interfaces")

    # eigrp
    p = csub.add_parser("eigrp")
    p.add_argument("--as-number", type=int, required=True)
    p.add_argument("--router-id", required=True)
    p.add_argument("--networks", nargs="+", required=True, help="network wildcard pairs")
    p.add_argument("--interfaces", nargs="*")

    # bgp
    p = csub.add_parser("bgp")
    p.add_argument("--as-number", type=int, required=True)
    p.add_argument("--router-id", required=True)
    p.add_argument("--networks", nargs="+", required=True, help="network mask pairs: 10.0.0.0 255.0.0.0")
    p.add_argument("--neighbors", nargs="+", required=True, help="neighbor_ip remote_as pairs")
    p.add_argument("--redistribute-connected", action="store_true")

    # acl-standard
    p = csub.add_parser("acl-standard")
    p.add_argument("--acl-id", required=True)
    p.add_argument("--permit", type=str, nargs="+", required=True, help="true/false for each entry")
    p.add_argument("--networks", nargs="+", required=True, help="network for each entry")
    p.add_argument("--wildcards", nargs="+", required=True, help="wildcard for each entry")

    # acl-extended
    p = csub.add_parser("acl-extended")
    p.add_argument("--acl-id", required=True)
    p.add_argument("--permit", type=str, nargs="+", required=True)
    p.add_argument("--protos", nargs="+", required=True)
    p.add_argument("--srcs", nargs="+", required=True)
    p.add_argument("--src-wilds", nargs="+", required=True)
    p.add_argument("--dsts", nargs="+", required=True)
    p.add_argument("--dst-wilds", nargs="+", required=True)
    p.add_argument("--eq", nargs="*", default=None)

    # acl-apply
    p = csub.add_parser("acl-apply")
    p.add_argument("--interface", required=True)
    p.add_argument("--acl-id", required=True)
    p.add_argument("--direction", choices=["in", "out"], default="in")

    # nat-static
    p = csub.add_parser("nat-static")
    p.add_argument("--inside-local", required=True)
    p.add_argument("--inside-global", required=True)
    p.add_argument("--interface")

    # nat-dynamic
    p = csub.add_parser("nat-dynamic")
    p.add_argument("--acl-id", required=True)
    p.add_argument("--pool", required=True)
    p.add_argument("--start-ip", required=True)
    p.add_argument("--end-ip", required=True)
    p.add_argument("--mask", required=True)
    p.add_argument("--overload", action="store_true")

    # nat-overload
    p = csub.add_parser("nat-overload")
    p.add_argument("--acl-id", required=True)
    p.add_argument("--interface", required=True)

    # nat-interface
    p = csub.add_parser("nat-interface")
    p.add_argument("--inside", required=True)
    p.add_argument("--outside", required=True)

    # dhcp-pool
    p = csub.add_parser("dhcp-pool")
    p.add_argument("--pool", required=True)
    p.add_argument("--network", required=True)
    p.add_argument("--mask", required=True)
    p.add_argument("--default-router", required=True)
    p.add_argument("--dns-servers", nargs="*")
    p.add_argument("--lease", type=int, default=1)

    # dhcp-exclude
    p = csub.add_parser("dhcp-exclude")
    p.add_argument("--start-ip", required=True)
    p.add_argument("--end-ip")

    # hsrp
    p = csub.add_parser("hsrp")
    p.add_argument("--interface", required=True)
    p.add_argument("--group", type=int, required=True)
    p.add_argument("--virtual-ip", required=True)
    p.add_argument("--priority", type=int, default=100)
    p.add_argument("--no-preempt", action="store_true")

    # snmp
    p = csub.add_parser("snmp")
    p.add_argument("--community", required=True)
    p.add_argument("--location")
    p.add_argument("--contact")
    p.add_argument("--acl-id")
    p.add_argument("--trap-host")

    # logging
    p = csub.add_parser("logging")
    p.add_argument("--host", required=True)
    p.add_argument("--trap-level", type=int, default=6, choices=range(0, 8))

    # ntp
    p = csub.add_parser("ntp")
    p.add_argument("--server", required=True)
    p.add_argument("--prefer", action="store_true")
    p.add_argument("--source-interface")

    # qos
    p = csub.add_parser("qos")
    p.add_argument("--class-name", required=True)
    p.add_argument("--match-acl", required=True)
    p.add_argument("--bandwidth", type=int)
    p.add_argument("--priority", type=int)
    p.add_argument("--queue-limit", type=int)
    p.add_argument("--policy-name")
    p.add_argument("--interface")

    # crypto-ike
    p = csub.add_parser("crypto-ike")
    p.add_argument("--priority", type=int, default=10)
    p.add_argument("--encryption", default="aes", choices=["des", "3des", "aes", "aes 192", "aes 256"])
    p.add_argument("--hash", default="sha", choices=["sha", "md5", "sha256", "sha384", "sha512"])
    p.add_argument("--dh-group", type=int, default=2, choices=[1, 2, 5, 14, 15, 16, 19, 20, 21, 24])
    p.add_argument("--lifetime", type=int, default=86400)

    # crypto-ipsec
    p = csub.add_parser("crypto-ipsec")
    p.add_argument("--transform", required=True)
    p.add_argument("--esp-encryption", default="esp-aes")
    p.add_argument("--esp-auth", default="esp-sha-hmac")

    # crypto-map
    p = csub.add_parser("crypto-map")
    p.add_argument("--map-name", required=True)
    p.add_argument("--seq", type=int, required=True)
    p.add_argument("--peer", required=True)
    p.add_argument("--transform-set", required=True)
    p.add_argument("--acl-id", required=True)
    p.add_argument("--local-address")
    p.add_argument("--psk")

    # crypto-map-apply
    p = csub.add_parser("crypto-map-apply")
    p.add_argument("--interface", required=True)
    p.add_argument("--map-name", required=True)

    return c


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

    fw_p = sub.add_parser("firmware-upgrade", help="Upgrade router IOS-XE firmware")
    fw_p.add_argument("--protocol", choices=["tftp", "ftp", "scp"], default="tftp")
    fw_p.add_argument("--server", help="TFTP/FTP/SCP server IP")
    fw_p.add_argument("--filename", help="Image filename on server")
    fw_p.add_argument("--auth-user", help="Username for FTP/SCP")
    fw_p.add_argument("--auth-pass", help="Password for FTP/SCP")
    fw_p.add_argument("--verify-only", action="store_true", help="Check current bootflash and boot variables")
    fw_p.add_argument("--reload", action="store_true", help="Reload router after upgrade")

    build_configure_parser(sub)

    args = parser.parse_args()

    conn = connect(args.host, args.username, args.password, args.port, args.secret)
    conn.enable()

    if args.action == "configure":
        cmd_configure(conn, args)
    elif args.action == "show":
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

    elif args.action == "firmware-upgrade":
        cmd_firmware_upgrade(conn, args.protocol, args.server, args.filename,
                            args.auth_user, args.auth_pass, args.verify_only, args.reload)

    conn.disconnect()


if __name__ == "__main__":
    main()
