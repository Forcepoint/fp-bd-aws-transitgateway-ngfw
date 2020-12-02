#!/usr/bin/python
import logging
import os
import sys

from smcConnector.AwsConnector import get_vpn
from smcConnector.Config import get_url, get_api_version, get_api_key

parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'Libs')
pem_dir = os.path.join(parent_dir, 'smc.pem')
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
        AutonomousSystem().create(name='ngfw-as', as_number=65000, comment='NGFW ASN')
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


def session_login():
    session.login(url=get_url(), api_key=get_api_key(), api_version=get_api_version(), verify=pem_dir)


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
    policy.fw_ipv4_access_rules.create(name='anyrule', sources='any', destinations='any', services='any',
                                       action=['allow'], comment='an allow rule', log_options=log_options)
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
    vpn_name, tunnel_1, tunnel_2 = get_vpn(public_ip)

    network_name = f'awsnetwork-{public_network}'
    try:
        Network.create(name=network_name, ipv4_network=public_network)
    except CreateElementFailed as err:
        logging.info(err)

    l3fw_policy('transit_gw_policy')
    policy = firewall_rule('transit_gw_policy')

    add_tunnel_to_engine(engine_name, '2000', tunnel_1.get('outside_ip'), tunnel_1.get('inside_ip_cidr'), 'tunnelA')
    add_tunnel_to_engine(engine_name, '2001', tunnel_2.get('outside_ip'), tunnel_2.get('inside_ip_cidr'), 'tunnelB')

    try:
        remote_gateway_first = external_gateway(
            name=f'{vpn_name}-{1}', endpoint_name='endpoint_1',
            address=tunnel_1.get('outside_ip'),
            network_name=network_name)  # site-to-site vpn connection VPN ID include number at the end
    except CreateElementFailed as err:
        logging.info(err)

    try:
        remote_gateway_second = external_gateway(
            name=f'{vpn_name}-{2}', endpoint_name='endpoint_2',
            address=tunnel_2.get('outside_ip'),
            network_name=network_name)  # site-to-site vpn connection VPN ID include number at the end
    except CreateElementFailed as err:
        logging.info(err)

    bgp_elements(64512, vpn_name, tunnel_1.get('gateway'), tunnel_2.get('gateway'),
                 engine_name)  # transit gateway : Amazon ASN inside ip is from tunnel of vpn - the /30

    add_dynamic_routing_antispoofing(engine_name)

    vpn_endpoint = Engine(engine_name).vpn_endpoint.get_contains(private_ip)
    vpn_endpoint.update(enabled=True)

    vpn_create_ipsec(engine_name, 2000, tunnel_1.get('pre_shared_key'), vpn_name, 1, remote_gateway_first)
    vpn_create_ipsec(engine_name, 2001, tunnel_2.get('pre_shared_key'), vpn_name, 2, remote_gateway_second)

    policy.upload(engine_name)

    session.logout()
