import json
import urllib.parse as urlparse
import smcConnector.Config as Config

address = urlparse.urlparse(Config.get_url())
port = address.port

json_string = {
    "smc-contact": {"address": address.hostname, "port": address.port, "apikey": Config.get_api_key(), "tls": True,
                    "check_certificate": False}, "location": "cloud", "auto-delete": False, "type": "single-firewall"}

with open("Cloudformations scripts/tg-ngfw-2-engines.json", "r") as jsonFile:
    data = json.load(jsonFile)

data['Parameters']['UserData']['Default'] = json.dumps(json_string)
data['Parameters']['BucketName']['Default'] = Config.get_lambda_bucket_name()

data['Resources']['ngfwSubnet1a']['Properties']['AvailabilityZone'] = Config.get_availability_zone_1()
data['Resources']['ngfwSubnet1b']['Properties']['AvailabilityZone'] = Config.get_availability_zone_2()

data['Resources']['NGFWTransitGateway1']['Properties']['ImageId'] = Config.get_ngfw_ami()
data['Resources']['NGFWTransitGateway2']['Properties']['ImageId'] = Config.get_ngfw_ami()

with open("tg-ngfw-2-engines.json", "w") as jsonFile:
    json.dump(data, jsonFile)
