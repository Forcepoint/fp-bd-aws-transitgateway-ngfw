#!/usr/bin/python
import json
import os
import sys
import time

from smcConnector.ipFomat import MyIPv4, ip_range_calculator, string_to_ip
from smcConnector.EngineCreation import engine_creation
from smcConnector.TransitGatewayBridge import smc_configuration

parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'Libs')
pem_dir = os.path.join(parent_dir, 'smc.pem')
sys.path.append(vendor_dir)

from crhelper import CfnResource

helper = CfnResource()
MASK = '255.255.255.0'
PROTECTED_NETWORK = '10.0.0.0/8'


def lambda_handler(event, context):
    helper(event, context)


@helper.create
@helper.update
def smc_config(event, _):
    time.sleep(150)
    engine_name = str(os.environ['engine_name'])
    private_ip = str(os.environ['private_ip'])
    public_ip = str(os.environ['public_ip'])

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

        smc_configuration(engine, public_ip_list[engine_list.index(engine)], private_ip_list[engine_list.index(engine)], str(public_network))

    return {
        'statusCode': 200,
        'body': json.dumps('SMC api configured, engine name: ' + engine_name)
    }


@helper.delete
def no_op(_, __):
    pass
