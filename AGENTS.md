# AGENTS.md

## Commands

```powershell
# Run a script
python hello.py --name "Alice"

# CSR 1000V automation agent
python router_agent.py --host <ip> --username admin --password cisco <action> [args]

# Available top-level actions:
#   show <command>       — any show command
#   config <cmd>...      — raw config commands
#   facts / health       — device info
#   backup / diff        — config management
#   audit                — security compliance scan
#   troubleshoot         — full device diagnostic bundle
#   ping / traceroute    — connectivity tests
#   apply-config <file>  — push config from file
#   save                 — write memory
#   deploy-vlan <id> <name>
#   watch <cmd> --interval 5
#   firmware-upgrade --protocol tftp --server 10.0.0.1 --filename csr1000v-universalk9.17.06.06a.SPA.bin [--reload]

# Configure subcommands (structured config by category):
python router_agent.py --host <ip> -u admin -p cisco configure interface --name GigabitEthernet1 --ip 10.0.0.1 --mask 255.255.255.0 --shutdown false
python router_agent.py --host <ip> -u admin -p cisco configure ospf --process 1 --router-id 1.1.1.1 --networks 10.0.0.0 0.0.0.255 --area 0
python router_agent.py --host <ip> -u admin -p cisco configure vlan --vlan-id 100 --name Users
python router_agent.py --host <ip> -u admin -p cisco configure bgp --as-number 65001 --router-id 1.1.1.1 --networks 10.0.0.0 255.0.0.0 --neighbors 192.168.1.1 65002
python router_agent.py --host <ip> -u admin -p cisco configure acl-standard --acl-id 10 --permit true --networks 192.168.1.0 --wildcards 0.0.0.255
python router_agent.py --host <ip> -u admin -p cisco configure nat-overload --acl-id 100 --interface GigabitEthernet0/0/0
python router_agent.py --host <ip> -u admin -p cisco configure hsrp --interface GigabitEthernet1 --group 1 --virtual-ip 192.168.1.254
python router_agent.py --host <ip> -u admin -p cisco configure crypto-ike --priority 10 --encryption aes --dh-group 5
python router_agent.py --host <ip> -u admin -p cisco configure crypto-map --map-name MYMAP --seq 10 --peer 203.0.113.1 --transform-set MYSET --acl-id 100 --psk mykey

# See all configure subcommands:
python router_agent.py --host <ip> -u admin -p cisco configure --help

# Run all tests (including router_config unit tests)
python -m pytest tests/ -v

# Run a single test
python -m pytest tests/test_router_config.py::test_ospf_cmds -v
```

## Structure

- `router_agent.py` — main CLI agent, dispatches to subcommands
- `router_config.py` — config builder module with functions for 28 IOS configuration categories
- `tests/test_router_config.py` — unit tests for every config builder function
- `tests/test_router_agent.py` — help-only smoke tests for every CLI action

## Configure categories (via `configure <category>`)

| Category | Purpose | Category | Purpose |
|----------|---------|----------|---------|
| system | hostname, banner, domain, NTP servers, enable secret | user | local username/privilege |
| aaa | authentication, authorization, accounting | ssh | SSH server v2, RSA keys |
| interface | physical interface IP, description, duplex, etc. | interface-vlan | SVI configuration |
| vlan | create named VLAN | trunk / access-port | switchport mode |
| port-security | MAC limiting, sticky, violation action | spanning-tree | STP mode (pvst/rpvst/mst) |
| static-route | IPv4 static routes | ospf | OSPF process, networks, areas |
| eigrp | EIGRP AS, networks | bgp | BGP AS, networks, neighbors |
| acl-standard / acl-extended | IP ACLs (numbered) | acl-apply | apply ACL to interface |
| nat-static / nat-dynamic | NAT translations | nat-overload | PAT on interface |
| nat-interface | mark inside/outside | dhcp-pool / dhcp-exclude | DHCP server |
| hsrp | First-hop redundancy | snmp | SNMP community, location |
| logging | syslog server | ntp | NTP server |
| qos | class-map, policy-map, service-policy | crypto-ike | ISAKMP policy (IPsec) |
| crypto-ipsec | transform-set | crypto-map / crypto-map-apply | IPsec tunnel + apply to interface |

## Conventions

- `router_config.py` functions are pure — they build `list[str]` of IOS commands, no SSH
- All configuration categories tested in `test_router_config.py`
- CLI scripts use `argparse` with `cwd=Path(__file__).resolve().parent.parent`
