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

def __describe_tgw_attachment(customer_gateway_vpn_id):
    response = boto3.client('ec2').describe_transit_gateway_attachments(
        Filters=[
            {
                'Name': 'resource-id',
                'Values': [
                    customer_gateway_vpn_id,
                ]
            },
        ])

    return response

def __describe_tgw_vpc_attachment():
    response = boto3.client('ec2').describe_transit_gateway_attachments(
        Filters=[
            {
                'Name': 'resource-type',
                'Values': [
                    'vpc',
                ]
            },
        ])

    return response

def __describe_tgw_route_table(transit_gateway_id):
    response = boto3.client('ec2').describe_transit_gateway_route_tables(
        Filters=[
            {
                'Name': 'transit-gateway-id',
                'Values': [
                    transit_gateway_id,
                ]
            },
        ])

    return response


def get_tgw_route_table(tgw_id):
    resp = __describe_tgw_route_table(tgw_id)
    print("TGW {} has route tables {}".format(tgw_id, resp))
    return resp['TransitGatewayRouteTables'][0]['TransitGatewayRouteTableId']

def get_vpn(public_ip):
    tunnel_1 = {'outside_ip': '', 'inside_ip_cidr': '', 'gateway_inside_ip': '',
                'pre_shared_key': '', 'cust_inside_ip': ''}
    tunnel_2 = {'outside_ip': '', 'inside_ip_cidr': '', 'gateway': '',
                'pre_shared_key': '', 'cust_inside_ip': ''}

    customer_gateway = __describe_customer_gateway(public_ip)
    cgw_id = customer_gateway['CustomerGateways'][0]['CustomerGatewayId']

    customer_gateway_configuration = __describe_vpn_connections(cgw_id)
    print("CGW  {} CFG {}".format(customer_gateway,
                                  customer_gateway_configuration))

    vpn_name = customer_gateway_configuration['VpnConnections'][0]['VpnConnectionId']
    tgw_attachment = __describe_tgw_attachment(vpn_name)
    print("CGW_id {} tgw_attachment {}".format(cgw_id, tgw_attachment))
    tgw_attachment_id = tgw_attachment['TransitGatewayAttachments'][0]['TransitGatewayAttachmentId']
    print("CGW_id {} tgw_attachment_id {} data {}"
          .format(cgw_id, tgw_attachment_id, tgw_attachment))

    tgw_attachment = __describe_tgw_vpc_attachment()
    tgw_vpc_attachment_id = tgw_attachment['TransitGatewayAttachments'][0]['TransitGatewayAttachmentId']
    doc = parse(customer_gateway_configuration['VpnConnections'][0]['CustomerGatewayConfiguration'])

    cidr = doc['vpn_connection']['ipsec_tunnel'][0]['customer_gateway']['tunnel_inside_address']['network_cidr']
    mask = doc['vpn_connection']['ipsec_tunnel'][0]['customer_gateway']['tunnel_inside_address']['network_mask']
    tunnel = MyIPv4(doc['vpn_connection']['ipsec_tunnel'][0]['customer_gateway']['tunnel_inside_address']['ip_address'])

    tunnel_1['outside_ip'] = doc['vpn_connection']['ipsec_tunnel'][0]['vpn_gateway']['tunnel_outside_address'][
        'ip_address']
    tunnel_1['inside_ip_cidr'] = f'{str(tunnel & MyIPv4(mask))}/{cidr}'
    tunnel_1['cust_inside_ip'] = str(tunnel)
    tunnel_1['gateway_inside_ip'] = doc['vpn_connection']['ipsec_tunnel'][0]['vpn_gateway']['tunnel_inside_address']['ip_address']
    tunnel_1['pre_shared_key'] = doc['vpn_connection']['ipsec_tunnel'][0]['ike']['pre_shared_key']

    cidr = doc['vpn_connection']['ipsec_tunnel'][1]['customer_gateway']['tunnel_inside_address']['network_cidr']
    mask = doc['vpn_connection']['ipsec_tunnel'][1]['customer_gateway']['tunnel_inside_address']['network_mask']
    tunnel = MyIPv4(doc['vpn_connection']['ipsec_tunnel'][1]['customer_gateway']['tunnel_inside_address']['ip_address'])

    tunnel_2['outside_ip'] = doc['vpn_connection']['ipsec_tunnel'][1]['vpn_gateway']['tunnel_outside_address'][
        'ip_address']
    tunnel_2['inside_ip_cidr'] = f'{str(tunnel & MyIPv4(mask))}/{cidr}'
    tunnel_2['cust_inside_ip'] = str(tunnel)
    tunnel_2['gateway_inside_ip'] = doc['vpn_connection']['ipsec_tunnel'][1]['vpn_gateway']['tunnel_inside_address']['ip_address']
    tunnel_2['pre_shared_key'] = doc['vpn_connection']['ipsec_tunnel'][1]['ike']['pre_shared_key']

    return vpn_name, tunnel_1, tunnel_2, tgw_attachment_id, tgw_vpc_attachment_id
