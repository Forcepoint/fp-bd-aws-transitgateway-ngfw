#!/usr/bin/python
import os
import sys
from smcConnector.Config import get_url, get_api_version, get_api_key
from smc import session


parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'Libs')
pem_dir = os.path.join(parent_dir, 'smc.pem')
sys.path.append(vendor_dir)


PROFILE_NAME = "aws_profile"

try:
    session.login(url=get_url(), api_key=get_api_key(), api_version=get_api_version(), verify=pem_dir)
    print(f'Your API Client: \'{session.current_user.name}\' can be reached')

except Exception as e:
    print(f'Error connecting: {e}')
session.logout()
