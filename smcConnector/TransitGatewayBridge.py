#!/usr/bin/python
import logging
import os
import sys
import time

from smcConnector.AwsConnector import get_vpn
from smcConnector.ipFomat import MyIPv4, string_to_ip
from smcConnector.common import session_login
from smcConnector import Config

parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'Libs')
sys.path.append(vendor_dir)

from smc import session
from smc.api.exceptions import CreatePolicyFailed, SMCException, CreateElementFailed, ElementNotFound
from smc.core.engine import Engine
from smc.elements.network import Network
from smc.policy import rule_elements
from smc.policy.layer3 import FirewallPolicy
from smc.routing.bgp import AutonomousSystem, ExternalBGPPeer, BGPPeering
from smc.vpn.elements import ExternalGateway, VPNProfile
from smc.vpn.route import TunnelEndpoint, RouteVPN


def add_dynamic_routing_antispoofing(engine_name):
    engine = Engine(engine_name)
    engine.dynamic_routing.update_antispoofing([Network('Any network')])

    engine.update()


def bgp_elements(aws_ASN, vgw_id, tunnel_inside_ip_1, tunnel_inside_ip_2, engine_name):
    engine = Engine(engine_name)
    try:
        AutonomousSystem().create(name='aws-as', as_number=aws_ASN, comment='aws VGW ASN')
    except CreateElementFailed as err:
        logging.info(err)

    try:
        AutonomousSystem().create(name='ngfw-as', as_number=65534, comment='NGFW ASN')
    except CreateElementFailed as err:
        logging.info(err)

    try:
        ExternalBGPPeer().create(name=f"peer-{vgw_id}-1"
                                 , comment="aws bgp peering element for tunnel_1"
                                 , neighbor_as=AutonomousSystem("aws-as")
                                 , neighbor_ip=tunnel_inside_ip_1)
    except CreateElementFailed as err:
        logging.info(err)

    try:
        ExternalBGPPeer().create(name=f"peer-{vgw_id}-2"
                                 , comment="aws bgp peering element for tunnel_2"
                                 , neighbor_as=AutonomousSystem("aws-as")
                                 , neighbor_ip=tunnel_inside_ip_2)
    except CreateElementFailed as err:
        logging.info(err)

    engine.dynamic_routing.update_ecmp(4)
    engine.dynamic_routing.bgp.enable(autonomous_system=AutonomousSystem(name='ngfw-as'),
                                      announced_networks=[Network('Any network')])

    try:
        BGPPeering.get('ngfw-bgp-peering')
    except ElementNotFound as err:
        BGPPeering.create(name='ngfw-bgp-peering')  # ngfw-bgp-peering

    Engine(engine_name).routing.get(2000).add_bgp_peering(BGPPeering('ngfw-bgp-peering'),
                                                          ExternalBGPPeer(f'peer-{vgw_id}-1'))
    Engine(engine_name).routing.get(2001).add_bgp_peering(BGPPeering('ngfw-bgp-peering'),
                                                          ExternalBGPPeer(f'peer-{vgw_id}-2'))

    engine.update()


def external_gateway(name, address, endpoint_name, network_name, status=True):
    external_endpoint = [{
        "address": address,
        "enabled": True,
        "name": endpoint_name
    }]

    gw = ExternalGateway.update_or_create(name, external_endpoint=external_endpoint,
                                          trust_all_cas=True, with_status=status)
    gw[0].vpn_site.create(name=f'remotesite-{endpoint_name}-{address}', site_element=[Network(network_name)])
    remote_gateway = TunnelEndpoint.create_ipsec_endpoint(gw[0])
    return remote_gateway


def add_tunnel_to_engine(engine_name, interface, address, cidr_range, zone_ref):
    try:
        Engine(engine_name).tunnel_interface.add_layer3_interface(
            interface_id=interface,
            address=address,
            network_value=cidr_range,
            zone_ref=zone_ref)

    except SMCException as err:
        logging.info(err)


def firewall_rule(policy_name):
    policy = FirewallPolicy(policy_name)
    log_options = rule_elements.LogOptions()
    log_options.log_level = 'stored'

    for r in policy.fw_ipv4_access_rules.all():
        if r.name == "anyrule":
            print("anyrule created already")
            return policy

    policy.fw_ipv4_access_rules.create(name='anyrule', sources='any',
                                       destinations='any', services='any',
                                       action=['allow'],
                                       comment='an allow rule',
                                       log_options=log_options)
    return policy


def l3fw_policy(name):
    try:
        FirewallPolicy.create(name=name, template='Firewall Inspection Template')
    except CreatePolicyFailed as err:
        logging.info(err)


def vpn_create_ipsec(engine_name, interface_id, preshared_key, vpn_name, vpn_num, remote_gateway):
    tunnel_if = Engine(engine_name).tunnel_interface.get(interface_id)
    local_gateway = TunnelEndpoint.create_ipsec_endpoint(Engine(engine_name).vpn.internal_gateway, tunnel_if)

    RouteVPN.create_ipsec_tunnel(
        name=f'{engine_name}-{vpn_name}-{vpn_num}',
        preshared_key=preshared_key,
        local_endpoint=local_gateway,
        remote_endpoint=remote_gateway,
        enabled=True,
        vpn_profile=VPNProfile('aws_profile'))


def smc_configuration(engine_name, public_ip, private_ip, public_network):
    session_login()
    vpn_name, tunnel_1, tunnel_2, cgw_tgw_attachment, vpc_tgw_attachment = get_vpn(public_ip)


    print("Tunnel 1 {}".format(tunnel_1))
    print("Tunnel 2 {}".format(tunnel_2))

    network_name = f'awsnetwork-{public_network}'
    try:
        Network.create(name=network_name, ipv4_network=public_network)
    except CreateElementFailed as err:
        logging.info(err)

    policy_name = Config.get_policy_name()
    if not policy_name:
        policy_name = "transit_gw_policy"


    tmp = tunnel_1.get('inside_ip_cidr').split("/")[0].split(".")
    tmp[3] = str(int(tmp[3]) + 2)
    inside_ip = ".".join(tmp)
    add_tunnel_to_engine(engine_name, '2000', tunnel_1.get('cust_inside_ip'),
                         tunnel_1.get('inside_ip_cidr'), 'tunnelA')

    tmp = tunnel_2.get('inside_ip_cidr').split("/")[0].split(".")
    tmp[3] = str(int(tmp[3]) + 2)
    inside_ip = ".".join(tmp)
    add_tunnel_to_engine(engine_name, '2001', tunnel_2.get('cust_inside_ip'),
                         tunnel_2.get('inside_ip_cidr'), 'tunnelB')

    remote_gateway_first = None
    try:
        remote_gateway_first = external_gateway(
            name=f'{vpn_name}-{1}', endpoint_name='endpoint_1',
            address=tunnel_1.get('outside_ip'),
            network_name=network_name)  # site-to-site vpn connection VPN ID include number at the end
    except CreateElementFailed as err:
        print("Got error {}".format(err))
        logging.info(err)

    remote_gateway_second = None
    try:
        remote_gateway_second = external_gateway(
            name=f'{vpn_name}-{2}', endpoint_name='endpoint_2',
            address=tunnel_2.get('outside_ip'),
            network_name=network_name)  # site-to-site vpn connection VPN ID include number at the end
    except CreateElementFailed as err:
        print("Got error {} for ep2".format(err))
        logging.info(err)

    bgp_elements(64512, vpn_name, tunnel_1.get('gateway_inside_ip'),
                 tunnel_2.get('gateway_inside_ip'),
                 engine_name)  # transit gateway : Amazon ASN inside ip is from tunnel of vpn - the /30

    add_dynamic_routing_antispoofing(engine_name)

    vpn_endpoint = Engine(engine_name).vpn_endpoint.get_contains(private_ip)
    vpn_endpoint.update(enabled=True)

    if remote_gateway_first:
        vpn_create_ipsec(engine_name, 2000, tunnel_1.get('pre_shared_key'),
                         vpn_name, 1, remote_gateway_first)
    if remote_gateway_second:
        vpn_create_ipsec(engine_name, 2001, tunnel_2.get('pre_shared_key'),
                         vpn_name, 2, remote_gateway_second)

    print("Using policy {}".format(policy_name))
    l3fw_policy(policy_name)
    upload_tries = 18
    while upload_tries:
        try:
            upload_tries = upload_tries - 1
            policy = firewall_rule(policy_name)
            policy.upload(engine_name)
            break
        except Exception as err:
            print("Got error {} for smc policy_upload".format(err))
            time.sleep(10)

    session.logout()
    return cgw_tgw_attachment


def remove_smc_engines(engine_name, public_ip, private_ip):
    session_login()
    MASK = '255.255.255.0'
    engine = Engine(engine_name)
    routes = RouteVPN.objects.all()
    gateways_to_delete = []
    for route in list(routes):
        route_name = route.name
        if engine_name in route_name:
            RouteVPN().get(route_name).delete()
            gateways_to_delete.append((route_name.split(engine_name)[-1])[1:])
    engine.delete()
    for gw in gateways_to_delete:
        ExternalGateway.get(gw).delete()
    public_base = MyIPv4(public_ip) & MyIPv4(MASK)
    public_network = string_to_ip(str(public_base) + '/24')
    Network.get(f'awsnetwork-{public_network}').delete()
    session.logout()
