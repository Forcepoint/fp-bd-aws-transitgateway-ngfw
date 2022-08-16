set -e
rm ./autoscale-tg-ngfw.json || true
rm ./myDeploymentPackage.zip || true
echo "Installing python3 requirements"
pip3 -q install -r ./Packager/requirements.txt -t ./smcConnector/Libs
chmod -R 755 ./smcConnector/.

python3 PackageHelper.py || (echo "Check that config.json has correct availability zone  configuration. AZ1 and AZ2 are mandatory"; exit 1)
cp ./smc.pem ./smcConnector/
zip --quiet -r ./myDeploymentPackage.zip ./smcConnector
zip --quiet -ur ./myDeploymentPackage.zip ./lambda_function.py
zip --quiet -ur ./myDeploymentPackage.zip ./config.json
rm -r ./smcConnector/Libs
rm ./smcConnector/smc.pem
