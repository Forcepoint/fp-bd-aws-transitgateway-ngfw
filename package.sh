rm ./tg-ngfw-2-engines.json
rm ./myDeploymentPackage.zip
pip3 install -r ./Packager/requirements.txt -t ./smcConnector/Libs
chmod -R 755 ./smcConnector/.
python3 PackageHelper.py
cp ./smc.pem ./smcConnector/
zip -r ./myDeploymentPackage.zip ./smcConnector
zip -ur ./myDeploymentPackage.zip ./lambda_function.py
zip -ur ./myDeploymentPackage.zip ./config.json
rm -r ./smcConnector/Libs
rm ./smcConnector/smc.pem
