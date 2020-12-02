#!/usr/bin/python
import os
import sys
import time

from smcConnector.Config import get_url, get_api_version, get_api_key

parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'Libs')
pem_dir = os.path.join(parent_dir, 'smc.pem')
sys.path.append(vendor_dir)

import smc
from smc import session
from smc.core.engine import Engine
from smc.elements.network import Router, Network
from smc.vpn.elements import VPNProfile

PROFILE_NAME = "aws_profile"


def engine_creation(engine_name, private_ip, public_ip, protected_network, router_ip, private_network):
    session.login(url=get_url(), api_key=get_api_key(), api_version=get_api_version(), verify=pem_dir)

    profile = VPNProfile.get_or_create(name=PROFILE_NAME)
    profile.update(capabilities=
    {
        'ike_v1': True,
        'aes128_for_ike': True,
        'aggressive_mode': False,
        'sha1_for_ike': True,
        'dh_group_2_for_ike': True,
        'pre_shared_key_for_ike': True,
        'rsa_signature_for_ike': False,
        'main_mode': True,
        'esp_for_ipsec': True,
        'aes128_for_ipsec': True,
        'sha1_for_ipsec': True,
        'sa_per_net': True,
        'pfs_dh_group_2_for_ipsec': True,
        'rsa_signature_for_ike': True,
        'vpn_client_sa_per_net': True
    },
        sa_life_time=28800,
        tunnel_life_time_seconds=3600,
        hybrid_authentication_for_mobile_vpn=True,
        trust_all_cas=True)
    # we should wait for the engine to be present
    engine = None
    while not engine:
        try:
            engine = Engine(engine_name)
        except smc.api.exceptions.ElementNotFound as e:
            print(e)
            print(engine)
            print("retrying in 3 sec")
            time.sleep(3)
    interface = engine.interface.get(0)

    # set_stream_logger(log_level=logging.DEBUG)
    for sub in interface.sub_interfaces():
        sub.data['dynamic'] = False
        sub.data['address'] = private_ip
        if 'dynamic_index' in sub.data:
            del sub.data['dynamic_index']
        sub.data['network_value'] = private_network
        sub.update()
    interface.update()

    ROUTER_NAME = "aws_default_router-{}".format(router_ip)
    if Router.objects.filter(ROUTER_NAME):
        router = Router(ROUTER_NAME)
    else:
        router = Router.create(ROUTER_NAME, router_ip)
    # update routing
    interface0 = engine.routing.get(0)
    for network in interface0:
        if network.name == 'Network (IPv4)':
            print("{} should be deleted".format(network))
            network.delete()
        if network.name == "network-{}".format(private_network):
            print("{} should be updated".format(network))
            interface0.add_static_route(gateway=router,
                                        destination=[Network('Any network')])
    # we need to add custom policy routing so advertised BGP routes are not used when
    # we source nat the traffic
    engine.data['policy_route'].append(
        dict(
            source=private_ip + '/32',
            destination=protected_network,
            gateway_ip=router_ip)
    )
    engine.update()

    # print(interface0.as_tree())
    ca = engine.contact_addresses.get(0, interface_ip=private_ip)
    ca.add_contact_address(public_ip, location='Default')

    session.logout()
