#!/usr/bin/python
import os
import json

import sys
import time

import boto3

from smcConnector.ipFomat import MyIPv4, string_to_ip
from smcConnector.EngineCreation import engine_creation
from smcConnector.TransitGatewayBridge import smc_configuration, remove_smc_engines

parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'Libs')
pem_dir = os.path.join(parent_dir, 'smc.pem')
sys.path.append(vendor_dir)

MASK = '255.255.255.0'
PROTECTED_NETWORK = '10.0.0.0/8'


def get_aws_client(resource):
    return boto3.client(resource)


def configure_smc_engines(engine_name, private_ip, public_ip):
    engine_list = engine_name.split(",")
    private_ip_list = private_ip.split(",")
    public_ip_list = public_ip.split(",")

    for engine in engine_list:
        base = MyIPv4(private_ip_list[engine_list.index(engine)]) & MyIPv4(MASK)
        router_ip = base + 1
        private_network = string_to_ip(str(base) + '/24')

        engine_creation(engine, private_ip_list[engine_list.index(engine)], public_ip_list[engine_list.index(engine)],
                        PROTECTED_NETWORK, str(router_ip), str(private_network))

        public_base = MyIPv4(public_ip_list[engine_list.index(engine)]) & MyIPv4(MASK)
        public_network = string_to_ip(str(public_base) + '/24')

        smc_configuration(engine, public_ip_list[engine_list.index(engine)], private_ip_list[engine_list.index(engine)],
                          str(public_network))


def scale_back_instances(event, context):
    client = get_aws_client('ec2')

    instance = client.describe_instances(
        InstanceIds=[
            event['detail']['EC2InstanceId'],
        ]
    )
    if instance:
        public_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']
        private_ip = instance['Reservations'][0]['Instances'][0]['PrivateIpAddress']
        instance_name = event['detail']['EC2InstanceId']

        # remove EIP association and release EIP
        eip_description = client.describe_addresses(
            PublicIps=[instance['Reservations'][0]['Instances'][0]['PublicIpAddress']])
        client.disassociate_address(
            AssociationId=eip_description['Addresses'][0]['AssociationId']
            # PublicIp='string'
        )
        client.release_address(
            AllocationId=eip_description['Addresses'][0]['AllocationId']
        )
        gateway = client.describe_customer_gateways(Filters=[
            {
                'Name': 'ip-address',
                'Values': [instance['Reservations'][0]['Instances'][0]['PublicIpAddress']]
            },
        ])['CustomerGateways'][0]['CustomerGatewayId']
        vpn_connections = client.describe_vpn_connections(Filters=[
            {
                'Name': 'customer-gateway-id',
                'Values': [
                    gateway,
                ]
            },
        ])['VpnConnections'][0]['VpnConnectionId']

        response_vpn = client.delete_vpn_connection(
            VpnConnectionId=vpn_connections
        )
        response_gwy = client.delete_customer_gateway(
            CustomerGatewayId=gateway
        )
    # last step
    remove_smc_engines(instance_name, public_ip, private_ip)


def scale_up_instances(event, context):
    client = get_aws_client('ec2')

    instance = client.describe_instances(
        InstanceIds=[
            event['detail']['EC2InstanceId'],
        ]
    )

    try:

        public_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']

    except KeyError as e:
        eip = client.allocate_address(Domain='vpc')
        public_ip = eip['PublicIp']
        allocation_id = eip['AllocationId']
        client.associate_address(AllocationId=allocation_id, InstanceId=event['detail']['EC2InstanceId'])

    private_ip = instance['Reservations'][0]['Instances'][0]['PrivateIpAddress']

    tg_gateways = client.describe_transit_gateways()
    for tg_gateway in tg_gateways['TransitGateways']:
        if tg_gateway['Tags'][0]['Value'] == 'test-tgw':
            transit_gateway_id = tg_gateway['TransitGatewayId']
    gws = client.describe_customer_gateways()

    create_gateway = True
    for customer_gateway in gws['CustomerGateways']:
        if customer_gateway['IpAddress'] == public_ip:
            create_gateway = False

    if create_gateway:
        customer_gateway = client.create_customer_gateway(BgpAsn=65534, PublicIp=public_ip, Type='ipsec.1')
        client.create_vpn_connection(CustomerGatewayId=customer_gateway['CustomerGateway']['CustomerGatewayId'],
                                     Type='ipsec.1',
                                     TransitGatewayId=transit_gateway_id,
                                     Options={
                                         'StaticRoutesOnly': False})
    time.sleep(150)
    configure_smc_engines(event['detail']['EC2InstanceId'], private_ip, public_ip)


def lambda_handler(event, context):
    print(event)
    if event is not None and type(event) is dict and 'source' in event.keys():
        if event['source'] == 'aws.autoscaling' \
                and event['detail']['LifecycleTransition'] == 'autoscaling:EC2_INSTANCE_LAUNCHING':
            scale_up_instances(event, context)
            return {
                'statusCode': 200,
                'body': json.dumps('SMC api configured, engine name: ' + event['detail']['EC2InstanceId'])
            }
        elif event['source'] == 'aws.autoscaling' \
                and event['detail']['LifecycleTransition'] == 'autoscaling:EC2_INSTANCE_TERMINATING':
            scale_back_instances(event, context)
            return {
                'statusCode': 200,
                'body': json.dumps('engine name: ' + event['detail']['EC2InstanceId'] + ' is removed')
            }
