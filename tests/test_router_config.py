import router_config as rc


def test_system_hostname():
    cmds = rc.system_cmds(hostname="Router1")
    assert "hostname Router1" in cmds


def test_system_banner():
    cmds = rc.system_cmds(banner="Authorized Access Only")
    assert "banner motd ^Authorized Access Only^" in cmds


def test_system_full():
    cmds = rc.system_cmds(hostname="R1", domain="example.com", nameservers=["8.8.8.8"], enable_secret="secret123")
    assert "hostname R1" in cmds
    assert "ip domain-name example.com" in cmds
    assert "ip name-server 8.8.8.8" in cmds
    assert "enable secret secret123" in cmds


def test_interface_cmds():
    cmds = rc.interface_cmds("GigabitEthernet1", ip_address="10.0.0.1", subnet_mask="255.255.255.0",
                             description="WAN", shutdown=False)
    assert "interface GigabitEthernet1" in cmds
    assert "ip address 10.0.0.1 255.255.255.0" in cmds
    assert "description WAN" in cmds
    assert "no shutdown" in cmds


def test_vlan_cmds():
    cmds = rc.vlan_cmds(100, name="Users")
    assert "vlan 100" in cmds
    assert "name Users" in cmds
    assert cmds[-1] == "exit"


def test_trunk_cmds():
    cmds = rc.trunk_cmds("GigabitEthernet1", native_vlan=99)
    assert "switchport mode trunk" in cmds
    assert "switchport trunk native vlan 99" in cmds


def test_access_port_cmds():
    cmds = rc.access_port_cmds("GigabitEthernet2", 10)
    assert "switchport access vlan 10" in cmds


def test_port_security_cmds():
    cmds = rc.port_security_cmds("GigabitEthernet1", max_mac=2, violation="restrict")
    assert "switchport port-security maximum 2" in cmds
    assert "switchport port-security violation restrict" in cmds


def test_static_route_cmds():
    cmds = rc.static_route_cmds("0.0.0.0", "0.0.0.0", "192.168.1.1", distance=10)
    assert "ip route 0.0.0.0 0.0.0.0 192.168.1.1 10" in cmds


def test_ospf_cmds():
    cmds = rc.ospf_cmds(1, "1.1.1.1", [("10.0.0.0", "0.0.0.255")], area=0)
    assert "router ospf 1" in cmds
    assert "router-id 1.1.1.1" in cmds
    assert "network 10.0.0.0 0.0.0.255 area 0" in cmds


def test_eigrp_cmds():
    cmds = rc.eigrp_cmds(100, "1.1.1.1", [("10.0.0.0", "0.0.0.255")])
    assert "router eigrp 100" in cmds
    assert "eigrp router-id 1.1.1.1" in cmds


def test_bgp_cmds():
    cmds = rc.bgp_cmds(65001, "1.1.1.1", [("10.0.0.0", "255.0.0.0")], [("192.168.1.1", 65002)])
    assert "router bgp 65001" in cmds
    assert "neighbor 192.168.1.1 remote-as 65002" in cmds
    assert "network 10.0.0.0 mask 255.0.0.0" in cmds


def test_acl_standard_cmds():
    cmds = rc.acl_standard_cmds(10, [(True, "192.168.1.0", "0.0.0.255")])
    assert "access-list 10 permit 192.168.1.0 0.0.0.255" in cmds


def test_acl_extended_cmds():
        cmds = rc.acl_extended_cmds(100, [(True, "tcp", "any", "any", "10.0.0.0", "0.0.0.255", "80")])
        assert "access-list 100 permit tcp any any 10.0.0.0 0.0.0.255 eq 80" in cmds


def test_nat_static_cmds():
    cmds = rc.nat_static_cmds("192.168.1.10", "203.0.113.10")
    assert any("ip nat inside source static" in c for c in cmds)


def test_nat_dynamic_cmds():
    cmds = rc.nat_dynamic_cmds(1, "MYPOOL", "203.0.113.1", "203.0.113.10", "255.255.255.0", overload=True)
    assert "ip nat pool MYPOOL 203.0.113.1 203.0.113.10 netmask 255.255.255.0" in cmds


def test_dhcp_pool_cmds():
    cmds = rc.dhcp_pool_cmds("LAN", "192.168.1.0", "255.255.255.0", "192.168.1.1", dns_servers=["8.8.8.8"])
    assert "ip dhcp pool LAN" in cmds
    assert "dns-server 8.8.8.8" in cmds


def test_hsrp_cmds():
    cmds = rc.hsrp_cmds("GigabitEthernet1", 1, "192.168.1.254", priority=150)
    assert "standby 1 ip 192.168.1.254" in cmds
    assert "standby 1 priority 150" in cmds
    assert "standby 1 preempt" in cmds


def test_snmp_cmds():
    cmds = rc.snmp_cmds("public", location="DC1", contact="admin@example.com")
    assert "snmp-server community public RO" in cmds
    assert "snmp-server location DC1" in cmds
    assert "snmp-server contact admin@example.com" in cmds


def test_logging_cmds():
    cmds = rc.logging_cmds("10.0.0.2")
    assert "logging host 10.0.0.2" in cmds
    assert "logging on" in cmds


def test_ntp_cmds():
    cmds = rc.ntp_cmds("pool.ntp.org", prefer=True, source_interface="Loopback0")
    assert "ntp server pool.ntp.org prefer" in cmds
    assert "ntp source Loopback0" in cmds


def test_qos_cmds():
    cmds = rc.qos_cmds("VOICE", 100, priority_kbps=1000, interface="GigabitEthernet1")
    assert "class-map match-all VOICE" in cmds
    assert "match access-group 100" in cmds
    assert "priority 1000" in cmds
    assert "service-policy output" in " ".join(cmds)


def test_crypto_ike_cmds():
    cmds = rc.crypto_ike_cmds(priority=20, encryption="3des", dh_group=5)
    assert "crypto isakmp policy 20" in cmds
    assert "encryption 3des" in cmds
    assert "group 5" in cmds


def test_crypto_ipsec_cmds():
    cmds = rc.crypto_ipsec_cmds("MYSET")
    assert "crypto ipsec transform-set MYSET esp-aes esp-sha-hmac" in cmds


def test_crypto_map_cmds():
    cmds = rc.crypto_map_cmds("MYMAP", 10, "203.0.113.1", "MYSET", 100, psk="mykey")
    assert "crypto isakmp key mykey address 203.0.113.1" in cmds
    assert "crypto map MYMAP 10 ipsec-isakmp" in cmds
    assert "set peer 203.0.113.1" in cmds


def test_aaa_cmds():
    cmds = rc.aaa_cmds()
    assert "aaa new-model" in cmds
    assert "aaa authentication login default local" in cmds


def test_user_cmds():
    cmds = rc.user_cmds("admin", "strongpass")
    assert "username admin privilege 15 secret strongpass" in cmds


def test_spanning_tree_cmds():
    cmds = rc.spanning_tree_cmds("mst")
    assert "spanning-tree mode mst" in cmds


def test_nat_interface_overload():
    cmds = rc.nat_interface_overload_cmds(100, "GigabitEthernet0/0/0")
    assert any("ip nat inside source list 100 interface GigabitEthernet0/0/0 overload" in c for c in cmds)


def test_dhcp_exclude():
    cmds = rc.dhcp_exclude_cmds("192.168.1.1", "192.168.1.10")
    assert "ip dhcp excluded-address 192.168.1.1 192.168.1.10" in cmds
    cmds2 = rc.dhcp_exclude_cmds("192.168.1.1")
    assert "ip dhcp excluded-address 192.168.1.1" in cmds2


def test_nat_inside_outside():
    cmds = rc.nat_inside_outside_cmds("GigabitEthernet0/0/1", "GigabitEthernet0/0/0")
    assert "interface GigabitEthernet0/0/1" in cmds
    assert "ip nat inside" in cmds
    assert "interface GigabitEthernet0/0/0" in cmds
    assert "ip nat outside" in cmds


def test_acl_apply():
    cmds = rc.acl_apply_cmds("GigabitEthernet1", 101, "out")
    assert "ip access-group 101 out" in cmds
