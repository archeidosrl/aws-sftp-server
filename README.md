
# Welcome to your CDK Python project!

This is a blank project for CDK development with Python.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!


# Project

## S3
After the `storage` bucket is created, create the user's relative folders: 
e.g.: if you want to create a sftp user named `FirstUser`, and you want more than one environment, create the following folders:
- `FirstUserDevelopment`
- `FirstUserStaging`
- `FirstUserProduction`
in the S3 bucket.
Repeat this process for all users you want to have access to your sftp server.

## AWS Secret Manager
Create a `key-value` secret in AWS Secret Manager and store public ssh keys for your sftp users. <br> 
- `key` would be the name of the sftp user.
- `value` would be the public ssh key itself.

## Cloudformation Templates
Now you've created as many ssh keys as users you want to have access to your sftp server. <br>
Now, edit `templates/sftp-server.yaml` file <br>

### `sftp-server.yaml`
1. `Parameters` section: add as many users name as many you've created previously.
    ``` yaml
    Parameters:
        [...]
        ### -------------------------- ###
        FirstUser:
            Type: String
            Description: User name used to retrieve the SSH key and pass to nested stack, create the sftp user
        SecondUser:
            Type: String
            Description: User name used to retrieve the SSH key and pass to nested stack, create the sftp user
        [ and so on ... ]
        ### -------------------------- ###
    ```
2. Now, head op at the botton of the `Resources` section: here, add (for each environment you want) as many SFTP users as you need.
    ``` yaml
    Resources:
        [...]
            # ---------------------------------------------------- SFTP Users ----------------------------------------------------
            
            ### Add as many user as needed ###
   
            FirstUserDevelopment:
                Type: 'AWS::CloudFormation::Stack'
                Properties:
                TemplateURL: !Sub 'https://${TemplateBucket}.s3.eu-west-1.amazonaws.com/sftp-user.yaml'
                Parameters:
                   SFTPServerId: !GetAtt SFTPServer.ServerId
                   UserName: TestStaging
                   SshPublicKey: !Sub '{{resolve:secretsmanager:${SecretName}:SecretString:${FirstUser}}}'
                   ProjectName: !Ref ProjectName
                   S3Bucket: !Ref S3Bucket
                   UserRoleArn: !Ref UserRoleArn
            
            FirstUserStaging:
                Type: 'AWS::CloudFormation::Stack'
                Properties:
                TemplateURL: !Sub 'https://${TemplateBucket}.s3.eu-west-1.amazonaws.com/sftp-user.yaml'
                Parameters:
                   SFTPServerId: !GetAtt SFTPServer.ServerId
                   UserName: TestStaging
                   SshPublicKey: !Sub '{{resolve:secretsmanager:${SecretName}:SecretString:${FirstUser}}}'
                   ProjectName: !Ref ProjectName
                   S3Bucket: !Ref S3Bucket
                   UserRoleArn: !Ref UserRoleArn
            
            FirstUserProduction:
                Type: 'AWS::CloudFormation::Stack'
                Properties:
                TemplateURL: !Sub 'https://${TemplateBucket}.s3.eu-west-1.amazonaws.com/sftp-user.yaml'
                Parameters:
                   SFTPServerId: !GetAtt SFTPServer.ServerId
                   UserName: TestProduction
                   SshPublicKey: !Sub '{{resolve:secretsmanager:${SecretName}:SecretString:${FirstUser}}}'
                   ProjectName: !Ref ProjectName
                   S3Bucket: !Ref S3Bucket
                   UserRoleArn: !Ref UserRoleArn
            
            [ and so on ... ]
            # ---------------------------------------------------- SFTP Users ----------------------------------------------------
    ```


## Lambda Function
In order to deploy the lambda function, create a zip file and upload it to the lambda function.
Example: let's zip and deploy ``start_stop_sftp_server`` lambda function.
``` bash
cd templates/lambda/start_stop_sftp_server

mkdir package

pip install -r requirements.txt -t package/

cp start_stop_sftp_server.py package/

cd package/

zip -r ../function.zip .

```


