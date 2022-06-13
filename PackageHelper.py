import sys
import json
import urllib.parse as urlparse
import smcConnector.Config as Config

address = urlparse.urlparse(Config.get_url())
port = address.port


def remove_subnet_elements(series, item, az):
    position = 0
    for subnets in series:
        if subnets['Ref'] == f'ngfwSubnet1{az}':
            del data['Resources']['EC2TGA52Z3K']['Properties']['SubnetIds'][position]
        position += 1

log_server_pool = Config.get_logserver_pool()
location = Config.get_location()

if not log_server_pool:
    log_server_pool = False

if not location:
    location = "cloud"

json_string = {
    "smc-contact": {"address": address.hostname, "port": address.port,
                    "apikey": Config.get_api_key(), "tls": True,
                    "check_certificate": False},
    "location": location, "auto-delete": False, "type": "single-firewall",
    "log-server-pool": log_server_pool
}

with open("Cloudformations scripts/autoscale-tg-ngfw.json", "r") as jsonFile:
    data = json.load(jsonFile)

data['Parameters']['UserData']['Default'] = json.dumps(json_string)
data['Parameters']['BucketName']['Default'] = Config.get_lambda_bucket_name()
data['Resources']['ngfwSubnet1a']['Properties']['AvailabilityZone'] = Config.get_availability_zone_1()
data['Resources']['NGFWAutoscalingGroup']['Properties']['AvailabilityZones'][0] = Config.get_availability_zone_1()

vpc_net = Config.get_vpc_network()
if vpc_net:
    data['Resources']['vpc0b40973e5aa01818f']['Properties']['CidrBlock'] = vpc_net


subnet1 = Config.get_availability_zone_1_subnet()
if vpc_net and not subnet1:
    print("Invalid config.json. VPC network {} given. But no availibity " \
          "zone 1 subnet".format(vpc_net))
    sys.exit(1)
if subnet1:
    data['Resources']['ngfwSubnet1a']['Properties']['CidrBlock'] = subnet1

if Config.get_availability_zone_2():
    data['Resources']['ngfwSubnet1b']['Properties']['AvailabilityZone'] = Config.get_availability_zone_2()
    data['Resources']['NGFWAutoscalingGroup']['Properties']['AvailabilityZones'][1] = Config.get_availability_zone_2()
    subnet = Config.get_availability_zone_2_subnet()
    if vpc_net and not subnet:
        print("Invalid config.json. VPC network {} given. But no availibity " \
              "zone 2 subnet".format(vpc_net))
        sys.exit(1)
    if subnet:
        data['Resources']['ngfwSubnet1b']['Properties']['CidrBlock'] = subnet

else:
    del data['Resources']['ngfwSubnet1b']
    del data['Resources']['RouteTableAssociationb']
    position = 0

    for subnets in data['Resources']['EC2TGA52Z3K']['Properties']['SubnetIds']:
        if subnets['Ref'] == 'ngfwSubnet1b':
            del data['Resources']['EC2TGA52Z3K']['Properties']['SubnetIds'][position]
        position += 1

    position = 0
    for subnets in data['Resources']['NGFWAutoscalingGroup']['Properties']['AvailabilityZones']:
        if subnets == 'ap-south-1b':
            del data['Resources']['NGFWAutoscalingGroup']['Properties']['AvailabilityZones'][position]
        position += 1

    position = 0
    for subnets in data['Resources']['NGFWAutoscalingGroup']['Properties']['VPCZoneIdentifier']:
        if subnets['Ref'] == 'ngfwSubnet1b':
            del data['Resources']['NGFWAutoscalingGroup']['Properties']['VPCZoneIdentifier'][position]
        position += 1

    position = 0
    for subnets in data['Resources']['NGFWAutoscalingGroup']['DependsOn']:
        if subnets == 'ngfwSubnet1b':
            del data['Resources']['NGFWAutoscalingGroup']['DependsOn'][position]
        position += 1

    position = 0
    for subnets in data['Resources']['NGFWLaunchTemplate']['DependsOn']:
        if subnets == 'ngfwSubnet1b':
            del data['Resources']['NGFWLaunchTemplate']['DependsOn'][position]
        position += 1

if Config.get_availability_zone_3():
    data['Resources']['ngfwSubnet1c']['Properties']['AvailabilityZone'] = Config.get_availability_zone_3()
    data['Resources']['NGFWAutoscalingGroup']['Properties']['AvailabilityZones'][2] = Config.get_availability_zone_3()
    subnet = Config.get_availability_zone_3_subnet();
    if vpc_net and not subnet:
        print("Invalid config.json. VPC network {} given. But no availibity " \
              "zone 3 subnet".format(vpc_net))
        sys.exit(1)
    if subnet:
        data['Resources']['ngfwSubnet1c']['Properties']['CidrBlock'] = subnet
else:
    del data['Resources']['ngfwSubnet1c']
    del data['Resources']['RouteTableAssociationc']
    position = 0

    for subnets in data['Resources']['EC2TGA52Z3K']['Properties']['SubnetIds']:
        if subnets['Ref'] == 'ngfwSubnet1c':
            del data['Resources']['EC2TGA52Z3K']['Properties']['SubnetIds'][position]
        position += 1

    position = 0
    for subnets in data['Resources']['NGFWAutoscalingGroup']['Properties']['AvailabilityZones']:
        if subnets == 'ap-south-1c':
            del data['Resources']['NGFWAutoscalingGroup']['Properties']['AvailabilityZones'][position]
        position += 1

    position = 0
    for subnets in data['Resources']['NGFWAutoscalingGroup']['Properties']['VPCZoneIdentifier']:
        if subnets['Ref'] == 'ngfwSubnet1c':
            del data['Resources']['NGFWAutoscalingGroup']['Properties']['VPCZoneIdentifier'][position]
        position += 1

    position = 0
    for subnets in data['Resources']['NGFWAutoscalingGroup']['DependsOn']:
        if subnets == 'ngfwSubnet1c':
            del data['Resources']['NGFWAutoscalingGroup']['DependsOn'][position]
        position += 1

    position = 0
    for subnets in data['Resources']['NGFWLaunchTemplate']['DependsOn']:
        if subnets == 'ngfwSubnet1c':
            del data['Resources']['NGFWLaunchTemplate']['DependsOn'][position]
        position += 1

data['Resources']['NGFWLaunchTemplate']['Properties']['LaunchTemplateData']['ImageId'] = Config.get_ngfw_ami()


out_file_name = "autoscale-tg-ngfw.json"
with open(out_file_name, "w") as jsonFile:
    json.dump(data, jsonFile)

name_prefix = Config.get_name_prefix()

import subprocess
if name_prefix:
    cmd = "sed -i.bak 's/test-tgw/{}/g' {}".format(name_prefix, out_file_name)
    ret = subprocess.run(cmd, shell=True)
    # print("{} -> {}".format(cmd, ret))

