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


json_string = {
    "smc-contact": {"address": address.hostname, "port": address.port, "apikey": Config.get_api_key(), "tls": True,
                    "check_certificate": False}, "location": "cloud", "auto-delete": False, "type": "single-firewall"}

with open("Cloudformations scripts/autoscale-tg-ngfw.json", "r") as jsonFile:
    data = json.load(jsonFile)

data['Parameters']['UserData']['Default'] = json.dumps(json_string)
data['Parameters']['BucketName']['Default'] = Config.get_lambda_bucket_name()
data['Resources']['ngfwSubnet1a']['Properties']['AvailabilityZone'] = Config.get_availability_zone_1()
data['Resources']['NGFWAutoscalingGroup']['Properties']['AvailabilityZones'][0] = Config.get_availability_zone_1()

if Config.get_availability_zone_2():
    data['Resources']['ngfwSubnet1b']['Properties']['AvailabilityZone'] = Config.get_availability_zone_2()
    data['Resources']['NGFWAutoscalingGroup']['Properties']['AvailabilityZones'][1] = Config.get_availability_zone_2()

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


with open("autoscale-tg-ngfw.json", "w") as jsonFile:
    json.dump(data, jsonFile)
