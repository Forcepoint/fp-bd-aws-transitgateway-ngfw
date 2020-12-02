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


def get_availability_zone_1(config_file=__config_file):
    return __get_configurations(config_file)['availability_zone_1']


def get_availability_zone_2(config_file=__config_file):
    return __get_configurations(config_file)['availability_zone_2']


def get_ngfw_ami(config_file=__config_file):
    return __get_configurations(config_file)['ngfw_ami']


def get_lambda_bucket_name(config_file=__config_file):
    return __get_configurations(config_file)['lambda_bucket_name']
