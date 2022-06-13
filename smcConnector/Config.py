import json
import os

parent_dir = os.path.abspath(os.path.dirname(__file__))
__config_file = os.path.join(parent_dir, '../config.json')


def __get_configurations(config_file=__config_file):
    with open(config_file, 'r') as jsonFile:
        parsed_json = json.load(jsonFile)
    jsonFile.close()
    return parsed_json


def get_url(config_file=__config_file):
    return __get_configurations(config_file)['url']


def get_api_key(config_file=__config_file):
    return __get_configurations(config_file)['api_key']


def get_api_version(config_file=__config_file):
    return __get_configurations(config_file)['api_version']


def get_region(config_file=__config_file):
    return __get_configurations(config_file)['region']

def get_vpc_network(config_file=__config_file):
    try:
        return __get_configurations(config_file)['vpc_network']
    except:
        False

def get_name_prefix(config_file=__config_file):
    try:
        return __get_configurations(config_file)['cloud_formation_name_prefix']
    except:
        False

def get_policy_name(config_file=__config_file):
    try:
        return __get_configurations(config_file)['policy_name']
    except:
        False

def get_logserver_pool(config_file=__config_file):
    try:
        return __get_configurations(config_file)['logserver_pool']
    except:
        False

def get_location(config_file=__config_file):
    try:
        return __get_configurations(config_file)['location']
    except:
        False

def get_protected_network(config_file=__config_file):
    try:
        return __get_configurations(config_file)['protected_network']
    except:
        False

def get_availability_zone_1(config_file=__config_file):
    return __get_configurations(config_file)['availability_zone_1']

def get_availability_zone_1_subnet(config_file=__config_file):
    try:
        return __get_configurations(config_file)['availability_zone_1_subnet']
    except:
        False

def get_availability_zone_1_subnet(config_file=__config_file):
    try:
        return __get_configurations(config_file)['availability_zone_1_subnet']
    except:
        False


def get_availability_zone_2(config_file=__config_file):
    return __get_configurations(config_file)['availability_zone_2']

def get_availability_zone_2_subnet(config_file=__config_file):
    try:
        return __get_configurations(config_file)['availability_zone_2_subnet']
    except:
        False

def get_availability_zone_3(config_file=__config_file):
    try:
        return __get_configurations(config_file)['availability_zone_3']
    except:
        False

def get_availability_zone_3_subnet(config_file=__config_file):
    try:
        return __get_configurations(config_file)['availability_zone_3_subnet']
    except:
        False

def get_ngfw_ami(config_file=__config_file):
    return __get_configurations(config_file)['ngfw_ami']


def get_lambda_bucket_name(config_file=__config_file):
    return __get_configurations(config_file)['lambda_bucket_name']
