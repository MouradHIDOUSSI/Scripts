"""Cisco CSR 1000V configuration builder — structured wrappers for IOS config."""


def system_cmds(hostname=None, banner=None, domain=None, nameservers=None, enable_secret=None):
    cmds = []
    if hostname:
        cmds.append(f"hostname {hostname}")
    if banner:
        cmds.append(f"banner motd ^{banner}^")
    if domain:
        cmds.append(f"ip domain-name {domain}")
    if nameservers:
        for ns in nameservers:
            cmds.append(f"ip name-server {ns}")
    if enable_secret:
        cmds.append(f"enable secret {enable_secret}")
    return cmds


def user_cmds(username, password, privilege=15):
    return [f"username {username} privilege {privilege} secret {password}"]


def aaa_cmds(auth_login="default", auth_enable="default"):
    return [
        "aaa new-model",
        f"aaa authentication login {auth_login} local",
        f"aaa authentication enable default {auth_enable} local",
        "aaa session-id common",
    ]


def ssh_cmds(domain, rsa_key_bits=2048):
    return [
        f"ip domain-name {domain}",
        f"crypto key generate rsa general-keys modulus {rsa_key_bits}",
        "ip ssh version 2",
        "ip ssh authentication-retries 3",
        "line vty 0 4",
        "transport input ssh",
        "login local",
        "exit",
    ]


def interface_cmds(
    interface,
    ip_address=None,
    subnet_mask=None,
    description=None,
    duplex=None,
    speed=None,
    mtu=None,
    shutdown=None,
    vrf=None,
):
    cmds = [f"interface {interface}"]
    if description:
        cmds.append(f"description {description}")
    if ip_address and subnet_mask:
        cmds.append(f"ip address {ip_address} {subnet_mask}")
    if duplex:
        cmds.append(f"duplex {duplex}")
    if speed:
        cmds.append(f"speed {speed}")
    if mtu:
        cmds.append(f"mtu {mtu}")
    if vrf:
        cmds.append(f"ip vrf forwarding {vrf}")
    if shutdown is True:
        cmds.append("shutdown")
    elif shutdown is False:
        cmds.append("no shutdown")
    cmds.append("exit")
    return cmds


def interface_vlan_cmds(vlan_id, ip_address=None, subnet_mask=None, description=None, shutdown=None):
    cmds = [f"interface Vlan{vlan_id}"]
    if description:
        cmds.append(f"description {description}")
    if ip_address and subnet_mask:
        cmds.append(f"ip address {ip_address} {subnet_mask}")
    if shutdown is True:
        cmds.append("shutdown")
    elif shutdown is False:
        cmds.append("no shutdown")
    cmds.append("exit")
    return cmds


def vlan_cmds(vlan_id, name=None):
    cmds = [f"vlan {vlan_id}"]
    if name:
        cmds.append(f"name {name}")
    cmds.append("exit")
    return cmds


def trunk_cmds(interface, allowed_vlans="all", native_vlan=None):
    cmds = [
        f"interface {interface}",
        "switchport trunk encapsulation dot1q",
        "switchport mode trunk",
        f"switchport trunk allowed vlan {allowed_vlans}",
    ]
    if native_vlan:
        cmds.append(f"switchport trunk native vlan {native_vlan}")
    cmds.append("exit")
    return cmds


def access_port_cmds(interface, vlan_id):
    return [
        f"interface {interface}",
        "switchport mode access",
        f"switchport access vlan {vlan_id}",
        "exit",
    ]


def port_security_cmds(interface, max_mac=1, violation="shutdown"):
    return [
        f"interface {interface}",
        "switchport port-security",
        f"switchport port-security maximum {max_mac}",
        f"switchport port-security violation {violation}",
        "switchport port-security mac-address sticky",
        "exit",
    ]


def spanning_tree_cmds(mode="rapid-pvst"):
    return [f"spanning-tree mode {mode}"]


def static_route_cmds(network, mask, next_hop, distance=None, vrf=None):
    cmd = f"ip route {network} {mask} {next_hop}"
    if distance:
        cmd += f" {distance}"
    if vrf:
        cmd = f"ip route vrf {vrf} {network} {mask} {next_hop}"
    return [cmd]


def ospf_cmds(process_id, router_id, networks, area=0, interfaces=None):
    cmds = [
        f"router ospf {process_id}",
        f"router-id {router_id}",
    ]
    for net, wildcard in networks:
        cmds.append(f"network {net} {wildcard} area {area}")
    if interfaces:
        for intf in interfaces:
            cmds.extend([
                f"interface {intf}",
                "ip ospf authentication message-digest",
                "exit",
            ])
    cmds.append("exit")
    return cmds


def eigrp_cmds(as_number, router_id, networks, interfaces=None):
    cmds = [
        f"router eigrp {as_number}",
        f"eigrp router-id {router_id}",
    ]
    for net, wildcard in networks:
        cmds.append(f"network {net} {wildcard}")
    if interfaces:
        for intf in interfaces:
            cmds.extend([
                f"interface {intf}",
                "ip authentication mode eigrp md5",
                "exit",
            ])
    cmds.append("exit")
    return cmds


def bgp_cmds(as_number, router_id, networks, neighbors, redistribute_connected=False):
    cmds = [
        f"router bgp {as_number}",
        f"bgp router-id {router_id}",
    ]
    for net, mask in networks:
        cmds.append(f"network {net} mask {mask}")
    for neigh, remote_as in neighbors:
        cmds.append(f"neighbor {neigh} remote-as {remote_as}")
        cmds.append(f"neighbor {neigh} description BGP-PEER-AS{remote_as}")
    if redistribute_connected:
        cmds.append("redistribute connected")
    cmds.append("exit")
    return cmds


def acl_standard_cmds(acl_id, entries):
    cmds = [f"access-list {acl_id} remark AI-generated"]
    for permit, network, wildcard in entries:
        action = "permit" if permit else "deny"
        cmds.append(f"access-list {acl_id} {action} {network} {wildcard}")
    return cmds


def acl_extended_cmds(acl_id, entries):
    cmds = [f"access-list {acl_id} remark AI-generated"]
    for permit, proto, src, src_wild, dst, dst_wild, eq in entries:
        action = "permit" if permit else "deny"
        cmd = f"access-list {acl_id} {action} {proto} {src} {src_wild} {dst} {dst_wild}"
        if eq:
            cmd += f" eq {eq}"
        cmds.append(cmd)
    return cmds


def acl_apply_cmds(interface, acl_id, direction="in"):
    return [
        f"interface {interface}",
        f"ip access-group {acl_id} {direction}",
        "exit",
    ]


def nat_static_cmds(inside_local, inside_global, interface=None):
    cmds = [f"ip nat inside source static {inside_local} {inside_global}"]
    if interface:
        cmds.append(f"ip nat inside source static {inside_local} {inside_global} interface {interface}")
    return cmds


def nat_dynamic_cmds(acl_id, pool_name, start_ip, end_ip, mask, overload=False):
    cmds = [
        f"ip nat pool {pool_name} {start_ip} {end_ip} netmask {mask}",
        f"ip nat inside source list {acl_id} pool {pool_name}",
    ]
    if overload:
        cmds.append(f"ip nat inside source list {acl_id} pool {pool_name} overload")
    return cmds


def nat_interface_overload_cmds(acl_id, interface):
    return [f"ip nat inside source list {acl_id} interface {interface} overload"]


def nat_inside_outside_cmds(inside_interface, outside_interface):
    return [
        f"interface {inside_interface}",
        "ip nat inside",
        "exit",
        f"interface {outside_interface}",
        "ip nat outside",
        "exit",
    ]


def dhcp_pool_cmds(pool_name, network, mask, default_router, dns_servers=None, lease_days=1):
    cmds = [
        f"ip dhcp pool {pool_name}",
        f"network {network} {mask}",
        f"default-router {default_router}",
        f"lease {lease_days}",
    ]
    if dns_servers:
        cmds.append(f"dns-server {' '.join(dns_servers)}")
    cmds.append("exit")
    return cmds


def dhcp_exclude_cmds(start_ip, end_ip=None):
    if end_ip:
        return [f"ip dhcp excluded-address {start_ip} {end_ip}"]
    return [f"ip dhcp excluded-address {start_ip}"]


def hsrp_cmds(interface, group, virtual_ip, priority=100, preempt=True):
    cmds = [
        f"interface {interface}",
        f"standby {group} ip {virtual_ip}",
        f"standby {group} priority {priority}",
    ]
    if preempt:
        cmds.append(f"standby {group} preempt")
    cmds.append("exit")
    return cmds


def snmp_cmds(community, location=None, contact=None, acl_id=None, trap_host=None):
    cmds = [
        f"snmp-server community {community} RO" + (f" {acl_id}" if acl_id else ""),
    ]
    if location:
        cmds.append(f"snmp-server location {location}")
    if contact:
        cmds.append(f"snmp-server contact {contact}")
    if trap_host:
        cmds.append(f"snmp-server host {trap_host}")
    return cmds


def logging_cmds(host, trap_level=6):
    return [
        "logging on",
        f"logging host {host}",
        f"logging trap {trap_level}",
    ]


def ntp_cmds(server, prefer=False, source_interface=None):
    cmd = f"ntp server {server}"
    if prefer:
        cmd += " prefer"
    cmds = [cmd]
    if source_interface:
        cmds.append(f"ntp source {source_interface}")
    return cmds


def qos_cmds(class_name, match_acl, bandwidth_kbps=None, priority_kbps=None, queue_limit=None, policy_name=None, interface=None):
    cmds = [
        f"class-map match-all {class_name}",
        f"match access-group {match_acl}",
        "exit",
    ]
    if not policy_name:
        policy_name = f"{class_name}-POLICY"
    cmds.extend([
        f"policy-map {policy_name}",
        f"class {class_name}",
    ])
    if bandwidth_kbps:
        cmds.append(f"bandwidth {bandwidth_kbps}")
    if priority_kbps:
        cmds.append(f"priority {priority_kbps}")
    if queue_limit:
        cmds.append(f"queue-limit {queue_limit}")
    cmds.append("exit")
    cmds.append("exit")
    if interface:
        cmds.extend([
            f"interface {interface}",
            f"service-policy output {policy_name}",
            "exit",
        ])
    return cmds


def crypto_ike_cmds(priority=10, encryption="aes", hash_alg="sha", dh_group=2, lifetime=86400):
    return [
        f"crypto isakmp policy {priority}",
        f"encryption {encryption}",
        f"hash {hash_alg}",
        f"authentication pre-share",
        f"group {dh_group}",
        f"lifetime {lifetime}",
        "exit",
    ]


def crypto_ipsec_cmds(transform_name, esp_encryption="esp-aes", esp_auth="esp-sha-hmac"):
    return [
        f"crypto ipsec transform-set {transform_name} {esp_encryption} {esp_auth}",
        "mode tunnel",
        "exit",
    ]


def crypto_map_cmds(
    map_name, seq, peer, transform_set, acl_id, local_address=None, psk=None,
):
    cmds = [
        f"crypto map {map_name} {seq} ipsec-isakmp",
        f"set peer {peer}",
        f"set transform-set {transform_set}",
        f"match address {acl_id}",
    ]
    if local_address:
        cmds.append(f"set {local_address}")
    cmds.append("exit")
    if psk:
        cmds.insert(0, f"crypto isakmp key {psk} address {peer}")
    return cmds


def crypto_map_apply_cmds(interface, map_name):
    return [
        f"interface {interface}",
        f"crypto map {map_name}",
        "exit",
    ]
