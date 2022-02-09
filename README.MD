# Python Serverless Demo

Powered by [serverless framework](https://www.serverless.com/)

#### Requirements
 1. Install aws-cli and configure the environment with your credentials
 2. Install docker and start its services (Windows)
 3. Install Python (3.9)  [download](https://www.python.org/downloads/macos/)
 4. Install node [download](https://nodejs.org/en/download/)
 5. Install Serverless

```bash
# Installing with npm
npm install -g serverless 

# OR installing without npm
curl -o- -L https://slss.io/install | bash
```

#### Setup
1. Create a project folder
```bash
PROJECT_NAME='python-serverless-demo'
mkdir $PROJECT_NAME
cd $PROJECT_NAME

git init # starts a git repository

npm init -f # create package.json
npm install --save-dev serverless-wsgi serverless-python-requirements serverless-dotenv-plugin # install serverless requirements

# serverless-wsgi - adapts requests for the flask format
# serverless-python-requirements - handles python packages

npm install --save-dev serverless-offline # to run locally
```

2. Create the main package, a test package and a main file on the main package
3. Create a `serverless.yml` file

```yml
service: python-serverless-demo # project name

# serverless plugins
plugins:
  - serverless-wsgi
  - serverless-python-requirements
  - serverless-offline # optional, to run locally
  - serverless-dotenv-plugin # to import .env variables during deploy

custom:
  wsgi:
    app: psd_service/endpoint_hall.app # lambda name: file_location.function_name ; app is the flask starter
    packRequirements: false
  pythonRequirements:
    dockerizePip: non-linux # if true docker must be installed and the service must be running (or non-linux on non-linux env), this is for cross-compiling non-python stuff

# files to exclude from package
package:
  exclude:
    - .gitignore
    - README.md
    - package.json
    - package-lock.json
    - requirements.txt
    - .git/**
    - node_modules/**
    - venv/**
    - .idea/**

# aws
provider:
  name: aws
  runtime: python3.9 # python version (3.9 is the latest https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html)
  stage: dev
  region: us-west-1 # aws region
  memorySize: 256 # optional, in MB, default is 1024

# lambdas
functions: # declare lambda functions
  http-handler:
    handler: wsgi_handler.handler
    name: "${self:service}-${self:provider.stage}" # optional, Deployed Lambda name
    events:
      - http: ANY /
      - http: 'ANY /{proxy+}'
```

4. Create a python environment and activate it
```bash
pip3.9 install virtualenv
python3.9 -m virtualenv -p python3.9 venv # same version as on serverless.yml

source venv/bin/activate # activate the enviroment, use `deactivate` to disable
```

 5. Install python packages (with env activated)
```bash
pip install flask
pip freeze > requirements.txt
```
if it is not a new install run `pip install -r requirements.txt`

6. Create your `.env` file and a `.gitignore`
7. Test locally with `sls wsgi serve --host 0.0.0.0 -p 8000` 
8. Deploy with `sls deploy`
9. Run tests with `pytest`

#### Going advanced
 1. Install more python packages
```bash
pip install boto3 requests pytest aws-xray-sdk
pip freeze > requirements.txt
# boto3 - aws - dynamo
# requests - make https requests
# pytest - unit tests
```
 2. Install dynamo local, the xray plugin and husk
```bash
npm install --save-dev serverless-dynamodb-local serverless-plugin-tracing husky
```
3. Update the  `serverless.yml` file
```yml
service: python-serverless-demo # project name

# serverless plugins
plugins:
  - serverless-wsgi
  - serverless-python-requirements
  - serverless-offline # optional, to run locally
  - serverless-dotenv-plugin # to import .env variables during deploy
  - serverless-dynamodb-local # simulate dynamo locally
  - serverless-plugin-tracing # plugin for xray

custom:
  wsgi:
    app: psd_service/endpoint_hall.app # \file_location.function_name ; app is the flask starter
    packRequirements: false
  pythonRequirements:
    dockerizePip: non-linux # if true docker must be installed and the service must be running (or non-linux on non-linux env), this is for cross-compiling non-python stuff
  dynamodbUsers: 'user-table-${self:provider.stage}' # define a dynamo table for users
  dynamodbTransactions: 'transaction-table-${self:provider.stage}' # define a dynamo table for transactions
  dynamodb: # for offline dynamo
    stages:
      - dev
    start:
      port: 8032
      migrate: true


# files to exclude from package
package:
  exclude:
    - .gitignore
    - README.md
    - package.json
    - package-lock.json
    - requirements.txt
    - .git/**
    - node_modules/**
    - venv/**
    - .idea/**
    - .serverless/**
    - .dynamodb/**

# aws
provider:
  name: aws
  runtime: python3.9 # python version (3.9 is the latest https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html)
  stage: dev
  region: us-west-1 # aws region
  memorySize: 256 # optional, in MB, default is 1024
  iamRoleStatements:
    - Effect: Allow # permissions for dynamo
      Action:
        - dynamodb:Query
        - dynamodb:Scan
        - dynamodb:GetItem
        - dynamodb:PutItem
        - dynamodb:UpdateItem
        - dynamodb:DeleteItem
      Resource:
        - { "Fn::GetAtt": [ "UsersTable", "Arn" ] } # resource name
        - { "Fn::GetAtt": [ "TransactionsTable", "Arn" ] } # resource name
    - Effect: Allow # X ray permissions
      Action:
        - "xray:PutTraceSegments"
        - "xray:PutTelemetryRecords"
      Resource:
        - "*"
  environment:
    DYNAMODB_USERS: ${self:custom.dynamodbUsers} # set env var for table name
    DYNAMODB_TRANSACTIONS: ${self:custom.dynamodbTransactions} # set env var for table name

# lambdas
functions: # declare lambda functions
  http-handler:
    handler: wsgi_handler.handler
    name: "${self:service}-${self:provider.stage}" # optional, Deployed Lambda name
    tracing: 'true' # enable xray
    events:
      - http: ANY /
      - http: 'ANY /{proxy+}'

# resources
resources:
  Resources:
    UsersTable: # resource name
      Type: 'AWS::DynamoDB::Table'
      Properties:
        AttributeDefinitions: # fields and types, define only fields used for HASH, RANGE in Key schema or GlobalSecondaryIndexes. The other are created automatically
          - AttributeName: id
            AttributeType: S # string, B- binary, S- String, N- Numeric
          - AttributeName: username
            AttributeType: S # string, B- binary, S- String, N- Numeric
        KeySchema: # table keys
          - AttributeName: id
            KeyType: HASH # Partition key
        GlobalSecondaryIndexes: # table indices
          - IndexName: username-index
            KeySchema:
              - AttributeName: username
                KeyType: HASH
            Projection:
              ProjectionType: ALL # (ALL | KEYS_ONLY | INCLUDE)
            ProvisionedThroughput: # read and write limits
              ReadCapacityUnits: 1 # reads per second
              WriteCapacityUnits: 1 # writes per second
        ProvisionedThroughput: # read and write limits
          ReadCapacityUnits: 1 # reads per second
          WriteCapacityUnits: 1 # writes per second
        TableName: ${self:custom.dynamodbUsers} # the table name
    TransactionsTable: # resource name
      Type: 'AWS::DynamoDB::Table'
      Properties:
        AttributeDefinitions: # fields and types, define only fields used for HASH, RANGE in Key schema or GlobalSecondaryIndexes. The other are created automatically
          - AttributeName: id
            AttributeType: S # string, B- binary, S- String, N- Numeric
          - AttributeName: occurredAtUTC
            AttributeType: S # Date stored as ISO-8601, B- binary, S- String, N- Numeric
        KeySchema: # table keys
          - AttributeName: id
            KeyType: HASH # Partition key
          - AttributeName: occurredAtUTC
            KeyType: RANGE # Sort key
        ProvisionedThroughput: # read and write limits
          ReadCapacityUnits: 1 # reads per second
          WriteCapacityUnits: 1 # writes per second
        TableName: ${self:custom.dynamodbTransactions} # the table name
```
 4. Install dynamo locally
```bash
sls dynamodb install
```

5. Add this key to your `package.json`

```
"husky": {  
  "hooks": {  
    "pre-commit": "pytest"  
 }  
}
```
6. Run `npx husky install && npm install`  to generate the hook

7. Test locally 
```bash
sls dynamodb start # to launch dynamo, run in another window or background
sls wsgi serve --host 0.0.0.0 -p 8000
``` 
8. Deploy with `sls deploy`


### Points for improvement

- [ ] Run tests on a docker container and other test improvements. Links below might help:
  - https://buddy.works/tutorials/integration-testing-for-aws-lambda-in-go-with-docker-compose
  - https://medium.com/@octoz/automate-your-serverless-api-integration-tests-locally-e2f41d3ec757
  - http://joshuaballoch.github.io/testing-lambda-functions/
- [ ] Distribute flask endpoints across multiple files. A single file can be a mess for huge projects.
- [ ] Get variables from Parameter Store, Secrets ...
  - https://www.serverless.com/framework/docs/providers/aws/guide/variables#reference-variables-using-the-ssm-parameter-store
- [ ] Implement SQS, SNS and other features to demonstrate