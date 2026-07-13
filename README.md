# Scripts

Python automation toolkit for network engineers — primary focus is **Cisco CSR 1000V** management via SSH (netmiko).

## Requirements

- Python 3.8+
- `pip install netmiko`

## Quick Start

```powershell
# Connect to a CSR 1000V and run commands
python router_agent.py --host <router-ip> --username admin --password <pass> show "show ip interface brief"
python router_agent.py --host <router-ip> --username admin --password <pass> facts
python router_agent.py --host <router-ip> --username admin --password <pass> health
```

## Router Agent — All Features

### Basic Operations

| Action | Description |
|--------|-------------|
| `show <command>` | Run any show command |
| `config <cmd>...` | Send raw config commands |
| `facts` | Device facts: model, version, serial, uptime |
| `health` | Quick health: interfaces, CPU, memory |

### Configuration Management

| Action | Description |
|--------|-------------|
| `backup` | Save running-config to `backups/` with timestamp |
| `diff <baseline>` | Diff current config against a baseline file |
| `apply-config <file>` | Push config lines from a text file |
| `save` | Write memory (copy run start) |
| `deploy-vlan <id> <name>` | Create a VLAN |

### Troubleshooting & Testing

| Action | Description |
|--------|-------------|
| `audit` | Security compliance scan (ACLs, banners, passwords, syslog, NTP) |
| `troubleshoot` | Full device bundle: version, config, interfaces, routes, logs, CPU, memory, OSPF, BGP |
| `ping <target>` | Ping from the router |
| `traceroute <target>` | Traceroute from the router |
| `watch <cmd> --interval <s>` | Poll a show command periodically (Ctrl+C to stop) |

### Structured Configuration (`configure <category>`)

28 configuration categories through the `configure` subcommand:

| Category | Purpose |
|----------|---------|
| `system` | hostname, banner, domain, name-servers, enable secret |
| `user` | local username with privilege level |
| `aaa` | authentication login, enable, new-model |
| `ssh` | SSH version 2, RSA keys, VTY transport |
| `interface` | IP, description, duplex, speed, MTU, shutdown |
| `interface-vlan` | SVI IP and description |
| `vlan` | Create named VLAN |
| `trunk` | 802.1Q trunk with allowed VLANs and native VLAN |
| `access-port` | Access port with VLAN assignment |
| `port-security` | MAC limiting, sticky learning, violation action |
| `spanning-tree` | PVST, Rapid-PVST, or MST mode |
| `static-route` | IPv4 static routes with optional distance and VRF |
| `ospf` | OSPF process, router-id, networks, areas |
| `eigrp` | EIGRP AS, router-id, networks |
| `bgp` | BGP AS, networks, neighbors, redistribute connected |
| `acl-standard` | Standard numbered ACLs |
| `acl-extended` | Extended numbered ACLs (proto, src, dst, port) |
| `acl-apply` | Apply ACL to interface (in/out) |
| `nat-static` | Static NAT (inside local → inside global) |
| `nat-dynamic` | Dynamic NAT pool |
| `nat-overload` | PAT on interface |
| `nat-interface` | Mark inside/outside interfaces |
| `dhcp-pool` | DHCP pool with network, router, DNS, lease |
| `dhcp-exclude` | Excluded DHCP addresses |
| `hsrp` | HSRP group with virtual IP, priority, preempt |
| `snmp` | SNMP community, location, contact, trap host |
| `logging` | Syslog server with trap level |
| `ntp` | NTP server with prefer and source interface |
| `qos` | Class-map, policy-map, service-policy |
| `crypto-ike` | ISAKMP policy (encryption, hash, DH group, lifetime) |
| `crypto-ipsec` | IPsec transform-set |
| `crypto-map` | Crypto map with peer, transform-set, ACL, PSK |
| `crypto-map-apply` | Apply crypto map to interface |

Example:
```powershell
python router_agent.py --host <ip> -u admin -p pass configure interface --name GigabitEthernet1 --ip 10.0.0.1 --mask 255.255.255.0 --shutdown false
python router_agent.py --host <ip> -u admin -p pass configure ospf --process 1 --router-id 1.1.1.1 --networks 10.0.0.0 0.0.0.255 --area 0
python router_agent.py --host <ip> -u admin -p pass configure bgp --as-number 65001 --router-id 1.1.1.1 --networks 10.0.0.0 255.0.0.0 --neighbors 192.168.1.1 65002
python router_agent.py --host <ip> -u admin -p pass configure acl-standard --acl-id 10 --permit true --networks 192.168.1.0 --wildcards 0.0.0.255
python router_agent.py --host <ip> -u admin -p pass configure nat-overload --acl-id 100 --interface GigabitEthernet0/0/0
```

### Firmware Upgrade

```powershell
# Check current state
python router_agent.py --host <ip> -u admin -p pass firmware-upgrade --verify-only

# Upgrade via TFTP
python router_agent.py --host <ip> -u admin -p pass firmware-upgrade --protocol tftp --server <tftp-ip> --filename csr1000v-universalk9.<version>.SPA.bin

# Upgrade with auto-reload
python router_agent.py --host <ip> -u admin -p pass firmware-upgrade --protocol tftp --server <tftp-ip> --filename <image> --reload
```

## Running Tests

```powershell
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_router_config.py -v
```

## Project Structure

```
Scripts/
├── router_agent.py        # Main CLI agent
├── router_config.py       # Config builder module (pure functions, no SSH)
├── hello.py               # Example script
├── requirements.txt       # Python dependencies
├── AGENTS.md              # OpenCode agent instructions
├── credentials.txt        # Local router credentials (gitignored)
└── tests/
    ├── test_hello.py
    ├── test_router_agent.py
    └── test_router_config.py
```
