# bd-aws-transitGateway-NGFW

![](template.png)

Requirements:
1. TLS certificate from Forcepoint SMC
2. Api Key for Forcepoint SMC
3. Address of the SMC API
4. Keypair named "ngfw-tgw-keypair" created in AWS
5. Ami of forcepoint NGFW engine for the region its being created for
6. Location of s3 bucket that the code is stored in

Basic setup

1. Obtain keys and licences and copy them to congig.json and smc.pem
2. Run package.sh in a linux environment
3. Copy zip folder to an s3 Bucket folder structure Lambda-Functions/config-smc/myDeploymentPackage.zip
4. Create new CloudFormation stack and upload tg-ngfw-2-engines.json