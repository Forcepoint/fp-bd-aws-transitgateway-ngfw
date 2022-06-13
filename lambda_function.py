#!/usr/bin/python
import os
import json

import sys
import time

import boto3

from smcConnector.ipFomat import MyIPv4, string_to_ip
from smcConnector.EngineCreation import engine_creation
from smcConnector.TransitGatewayBridge import smc_configuration, remove_smc_engines
import smcConnector.Config as Config
from smcConnector.AwsConnector import get_tgw_route_table, get_vpn
parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'Libs')
pem_dir = os.path.join(parent_dir, 'smc.pem')
sys.path.append(vendor_dir)

MASK = '255.255.255.0'
PROTECTED_NETWORK = '10.0.0.0/8'


def get_aws_client(resource):
    return boto3.client(resource)


def attach_vpn_to_transit_gw(engine_name, public_ip, tgw):
    engine_list = engine_name.split(",")
    tgw_route_table = get_tgw_route_table(tgw)
    client = get_aws_client('ec2')
    public_ip_list = public_ip.split(",")

    for engine in engine_list:
        i = 12
        assoc_done = False
        vpn_name, tunnel_1, tunnel_2, cgw_tgw_attachment, vpc_tgw_attachment = \
            get_vpn(public_ip_list[engine_list.index(engine)])

        while i > 0:
            try:
                if not assoc_done:
                    response = client.associate_transit_gateway_route_table(
                        TransitGatewayRouteTableId=tgw_route_table,
                        TransitGatewayAttachmentId=cgw_tgw_attachment)
                    print("tgw VPN route assocation attachment OK! RESP {}".format(response))
                    assoc_done = True
                response = client.enable_transit_gateway_route_table_propagation(
                    TransitGatewayRouteTableId=tgw_route_table,
                    TransitGatewayAttachmentId=cgw_tgw_attachment)
                print("tgw VPN route propagation OK! RESP {}".format(response))
                break
            except Exception as e:
                print("tgw route attachment error {}".format(e))
                time.sleep(10)

            i = i - 1

        ret = client.modify_transit_gateway_vpc_attachment(
            TransitGatewayAttachmentId=vpc_tgw_attachment,
            Options={
                'ApplianceModeSupport': 'enable'
            }
        )
        print("modifided tgw vpc attchemnt {} ret={}"
              .format(vpc_tgw_attachment, ret))

def configure_smc_engines(engine_name, private_ip, public_ip):
    engine_list = engine_name.split(",")
    private_ip_list = private_ip.split(",")
    public_ip_list = public_ip.split(",")

    protected_network = Config.get_protected_network()
    if not protected_network:
        protected_network = PROTECTED_NETWORK

    for engine in engine_list:
        base = MyIPv4(private_ip_list[engine_list.index(engine)]) & MyIPv4(MASK)
        router_ip = base + 1
        private_network = string_to_ip(str(base) + '/24')

        engine_creation(engine, private_ip_list[engine_list.index(engine)],
                        public_ip_list[engine_list.index(engine)],
                        protected_network, str(router_ip), str(private_network))

        public_base = MyIPv4(public_ip_list[engine_list.index(engine)]) & MyIPv4(MASK)
        public_network = string_to_ip(str(public_base) + '/24')

        smc_configuration(engine,
                          public_ip_list[engine_list.index(engine)],
                          private_ip_list[engine_list.index(engine)],
                          str(public_network))

def scale_back_instances(event, context):
    client = get_aws_client('ec2')

    instance = client.describe_instances(
        InstanceIds=[
            event['detail']['EC2InstanceId'],
        ]
    )
    if instance:
        print("Instance down {}".format(instance))
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
        public_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']
        gateway = client.describe_customer_gateways(Filters=[
            {
                'Name': 'ip-address',
                'Values': [ public_ip ]
            },
        ])['CustomerGateways'][0]['CustomerGatewayId']
        print("GW {} for {}".format(gateway, public_ip))
        vpn_connections = client.describe_vpn_connections(Filters=[
            {
                'Name': 'customer-gateway-id',
                'Values': [
                    gateway,
                ]
            }
        ])
        print("VPN connections {}".format(vpn_connections))
        vpn_connections = vpn_connections['VpnConnections'][0]['VpnConnectionId']

        response_vpn = client.delete_vpn_connection(
            VpnConnectionId=vpn_connections
        )
        response_gwy = client.delete_customer_gateway(
            CustomerGatewayId=gateway
        )
    # last step
    remove_smc_engines(instance_name, public_ip, private_ip)
    print("Scaling down ok")


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
    tgw_name = Config.get_name_prefix()
    if not tgw_name:
        tgw_name = "test-tgw"

    transit_gateway_id = False
    for tg_gateway in tg_gateways['TransitGateways']:
        print("Checking TGW {} for name {}".format(tg_gateway, tgw_name))
        if tg_gateway['State'] == 'available' and \
           tg_gateway['Tags'][0]['Value'] == tgw_name:
            transit_gateway_id = tg_gateway['TransitGatewayId']
            print("Found TGW {}".format(transit_gateway_id))

    gws = client.describe_customer_gateways()
    create_gateway = True

    if not transit_gateway_id:
        print("Did not find TGW {}", tgw_name)
        return

    for customer_gateway in gws['CustomerGateways']:
        if customer_gateway['IpAddress'] == public_ip:
            print("Using customer GW {}".format(customer_gateway))
            create_gateway = False

    if create_gateway:
        customer_gateway = client.create_customer_gateway(BgpAsn=65534, PublicIp=public_ip, Type='ipsec.1')
        client.create_vpn_connection(CustomerGatewayId=customer_gateway['CustomerGateway']['CustomerGatewayId'],
                                     Type='ipsec.1',
                                     TransitGatewayId=transit_gateway_id,
                                     Options={
                                         'StaticRoutesOnly': False})
    time.sleep(120) # Let the transit gatway and attachment go active
    configure_smc_engines(event['detail']['EC2InstanceId'],
                          private_ip, public_ip)
    time.sleep(45) # Policy upload and VPN UP for transit gateway
    attach_vpn_to_transit_gw(event['detail']['EC2InstanceId'],
                          public_ip, transit_gateway_id);



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
