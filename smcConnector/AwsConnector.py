#!/usr/bin/python
import boto3
from xmltodict import parse

from smcConnector.ipFomat import MyIPv4


def __describe_customer_gateway(public_ip):
    response = boto3.client('ec2').describe_customer_gateways(
        Filters=[
            {
                'Name': 'ip-address',
                'Values': [
                    public_ip,
                ]
            },
        ]
    )
    return response


def __describe_vpn_connections(customer_gateway_id):
    response = boto3.client('ec2').describe_vpn_connections(
        Filters=[
            {
                'Name': 'customer-gateway-id',
                'Values': [
                    customer_gateway_id,
                ]
            },
        ])

    return response


def get_vpn(public_ip):
    tunnel_1 = {'outside_ip': '', 'inside_ip_cidr': '', 'gateway': '', 'pre_shared_key': ''}
    tunnel_2 = {'outside_ip': '', 'inside_ip_cidr': '', 'gateway': '', 'pre_shared_key': ''}

    customer_gateway = __describe_customer_gateway(public_ip)
    customer_gateway_configuration = __describe_vpn_connections(
        customer_gateway['CustomerGateways'][0]['CustomerGatewayId'])
    vpn_name = customer_gateway_configuration['VpnConnections'][0]['VpnConnectionId']

    doc = parse(customer_gateway_configuration['VpnConnections'][0]['CustomerGatewayConfiguration'])

    cidr = doc['vpn_connection']['ipsec_tunnel'][0]['customer_gateway']['tunnel_inside_address']['network_cidr']
    mask = doc['vpn_connection']['ipsec_tunnel'][0]['customer_gateway']['tunnel_inside_address']['network_mask']
    tunnel = MyIPv4(doc['vpn_connection']['ipsec_tunnel'][0]['customer_gateway']['tunnel_inside_address']['ip_address'])

    tunnel_1['outside_ip'] = doc['vpn_connection']['ipsec_tunnel'][0]['vpn_gateway']['tunnel_outside_address'][
        'ip_address']
    tunnel_1['inside_ip_cidr'] = f'{str(tunnel & MyIPv4(mask))}/{cidr}'
    tunnel_1['gateway'] = str(tunnel & MyIPv4(mask))
    tunnel_1['pre_shared_key'] = doc['vpn_connection']['ipsec_tunnel'][0]['ike']['pre_shared_key']

    cidr = doc['vpn_connection']['ipsec_tunnel'][1]['customer_gateway']['tunnel_inside_address']['network_cidr']
    mask = doc['vpn_connection']['ipsec_tunnel'][1]['customer_gateway']['tunnel_inside_address']['network_mask']
    tunnel = MyIPv4(doc['vpn_connection']['ipsec_tunnel'][1]['customer_gateway']['tunnel_inside_address']['ip_address'])

    tunnel_2['outside_ip'] = doc['vpn_connection']['ipsec_tunnel'][1]['vpn_gateway']['tunnel_outside_address'][
        'ip_address']
    tunnel_2['inside_ip_cidr'] = f'{str(tunnel & MyIPv4(mask))}/{cidr}'
    tunnel_2['gateway'] = str(tunnel & MyIPv4(mask))
    tunnel_2['pre_shared_key'] = doc['vpn_connection']['ipsec_tunnel'][1]['ike']['pre_shared_key']

    return vpn_name, tunnel_1, tunnel_2
