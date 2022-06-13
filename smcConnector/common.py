""" Provide common util functions """

import os
import sys
import urllib3
from smcConnector.Config import get_url, get_api_version, get_api_key

PARENT_DIR = os.path.abspath(os.path.dirname(__file__))
VENDOR_DIR = os.path.join(PARENT_DIR, 'Libs')
PEM_FILE = os.path.join(PARENT_DIR, 'smc.pem')

sys.path.append(VENDOR_DIR)

import smc
from smc import session

def session_login():
    """
    Login to SMC with API. If PEM_FILE is exists and non zero 0, then
    certifiicate verification is done
    """
    do_verify = False
    try:
        file_size = os.path.getsize(PEM_FILE)
        if file_size != 0:
            do_verify = PEM_FILE
    except OSError:
        pass

    if not do_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    session.login(url=get_url(), api_key=get_api_key(),
                  api_version=get_api_version(), verify=do_verify)
