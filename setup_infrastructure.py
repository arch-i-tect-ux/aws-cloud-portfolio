#!/usr/bin/env python3
"""
AWS Portfolio Infrastructure Setup
====================================
Run this script to create all required AWS resources.

BEFORE RUNNING:
  pip install boto3
  aws configure   (enter your Access Key ID, Secret, region: us-east-1)

WHAT THIS CREATES:
  - DynamoDB table: portfolio-contacts
  - IAM role for Lambda
  - Lambda functions (contact_form, get_submissions)
  - API Gateway with two routes
  - CloudWatch log groups
  - S3 bucket for static assets (free tier)

COST: $0 on AWS Free Tier
"""

import boto3
import json
import zipfile
import io
import time

REGION        = "us-east-1"
TABLE_NAME    = "portfolio-contacts"
ROLE_NAME     = "portfolio-lambda-role"
CONTACT_FN    = "portfolio-contact-form"
GET_FN        = "portfolio-get-submissions"
API_NAME      = "portfolio-api"
S3_BUCKET     = "portfolio-assets-YOUR-INITIALS"   # <-- make unique, lowercase only

session = boto3.Session(region_name=REGION)
iam      = session.client("iam")
dynamo   = session.client("dynamodb")
lmbda    = session.client("lambda")
apigw    = session.client("apigatewayv2")
logs     = session.client("logs")
s3       = session.client("s3")
sts      = session.client("sts")

ACCOUNT_ID = sts.get_caller_identity()["Account"]


def step(msg):
    print(f"\n{'='*55}")
    print(f"  {msg}")
    print(f"{'='*55}")


def create_dynamodb_table():
    step("1/7  Creating DynamoDB table")
    try:
        dynamo.create_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=[
                {"AttributeName": "submission_id", "AttributeType": "S"}
            ],
            KeySchema=[
                {"AttributeName": "submission_id", "KeyType": "HASH"}
            ],
            BillingMode="PAY_PER_REQUEST"   # Free tier — no provisioned capacity needed
        )
        print(f"  ✓ Table '{TABLE_NAME}' created (PAY_PER_REQUEST — free tier eligible)")
    except dynamo.exceptions.ResourceInUseException:
        print(f"  ✓ Table '{TABLE_NAME}' already exists — skipping")


def create_iam_role():
    step("2/7  Creating IAM role for Lambda")
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    try:
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Lambda execution role for portfolio project"
        )
        role_arn = role["Role"]["Arn"]
        print(f"  ✓ Role created: {role_arn}")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=ROLE_NAME)["Role"]["Arn"]
        print(f"  ✓ Role already exists: {role_arn}")

    # Attach policies
    policies = [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",  # CloudWatch logs
        "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
        "arn:aws:iam::aws:policy/AmazonSESFullAccess",
        "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
    ]
    for p in policies:
        iam.attach_role_policy(RoleName=ROLE_NAME, PolicyArn=p)
        print(f"  ✓ Attached: {p.split('/')[-1]}")

    print("  Waiting 10s for IAM propagation...")
    time.sleep(10)
    return role_arn


def zip_lambda(folder_path):
    """Zip a lambda folder into bytes for deployment."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        import os
        for fname in os.listdir(folder_path):
            fpath = os.path.join(folder_path, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, fname)
    buf.seek(0)
    return buf.read()


def deploy_lambda_functions(role_arn):
    step("3/7  Deploying Lambda functions")
    functions = [
        ("lambda/contact_form",   CONTACT_FN, "Contact form → DynamoDB + SES"),
        ("lambda/get_submissions", GET_FN,     "Read submissions from DynamoDB")
    ]
    arns = {}
    for folder, name, desc in functions:
        code = zip_lambda(folder)
        try:
            resp = lmbda.create_function(
                FunctionName=name,
                Runtime="python3.12",
                Role=role_arn,
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": code},
                Description=desc,
                Timeout=30,
                MemorySize=128,
                Environment={"Variables": {"TABLE_NAME": TABLE_NAME}}
            )
            arns[name] = resp["FunctionArn"]
            print(f"  ✓ Created: {name}")
        except lmbda.exceptions.ResourceConflictException:
            lmbda.update_function_code(FunctionName=name, ZipFile=code)
            arns[name] = lmbda.get_function(FunctionName=name)["Configuration"]["FunctionArn"]
            print(f"  ✓ Updated: {name}")
    return arns


def create_api_gateway(fn_arns):
    step("4/7  Creating API Gateway (HTTP API)")
    try:
        api = apigw.create_api(
            Name=API_NAME,
            ProtocolType="HTTP",
            CorsConfiguration={
                "AllowOrigins": ["*"],
                "AllowMethods": ["GET", "POST", "OPTIONS"],
                "AllowHeaders": ["Content-Type"]
            }
        )
        api_id  = api["ApiId"]
        api_url = api["ApiEndpoint"]
        print(f"  ✓ API created: {api_url}")

        # Create routes + integrations
        routes = [
            ("POST /contact",      fn_arns[CONTACT_FN]),
            ("GET  /submissions",  fn_arns[GET_FN])
        ]
        for route_key, fn_arn in routes:
            integration = apigw.create_integration(
                ApiId=api_id,
                IntegrationType="AWS_PROXY",
                IntegrationUri=fn_arn,
                PayloadFormatVersion="2.0"
            )
            apigw.create_route(
                ApiId=api_id,
                RouteKey=route_key.strip(),
                Target=f"integrations/{integration['IntegrationId']}"
            )
            # Grant API Gateway permission to invoke Lambda
            fn_name = fn_arn.split(":")[-1]
            lmbda.add_permission(
                FunctionName=fn_name,
                StatementId=f"apigw-{fn_name}-{int(time.time())}",
                Action="lambda:InvokeFunction",
                Principal="apigateway.amazonaws.com",
                SourceArn=f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*/*"
            )
            print(f"  ✓ Route: {route_key.strip()}")

        # Deploy
        apigw.create_stage(ApiId=api_id, StageName="$default", AutoDeploy=True)
        return api_url

    except Exception as e:
        print(f"  ! API Gateway error: {e}")
        return None


def create_s3_bucket():
    step("5/7  Creating S3 bucket for static assets")
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=S3_BUCKET)
        else:
            s3.create_bucket(
                Bucket=S3_BUCKET,
                CreateBucketConfiguration={"LocationConstraint": REGION}
            )
        print(f"  ✓ Bucket created: {S3_BUCKET}")
    except Exception as e:
        print(f"  ! S3: {e}")


def create_cloudwatch_alarms():
    step("6/7  Creating CloudWatch log groups")
    for fn in [CONTACT_FN, GET_FN]:
        try:
            logs.create_log_group(logGroupName=f"/aws/lambda/{fn}")
            logs.put_retention_policy(
                logGroupName=f"/aws/lambda/{fn}",
                retentionInDays=30
            )
            print(f"  ✓ Log group: /aws/lambda/{fn} (30-day retention)")
        except logs.exceptions.ResourceAlreadyExistsException:
            print(f"  ✓ Log group already exists: /aws/lambda/{fn}")


def print_summary(api_url):
    step("7/7  Setup complete!")
    print(f"""
  Resources created:
  ─────────────────────────────────────────────
  DynamoDB Table   {TABLE_NAME}
  Lambda (contact) {CONTACT_FN}
  Lambda (read)    {GET_FN}
  API Gateway      {api_url or 'check AWS console'}
  S3 Bucket        {S3_BUCKET}
  CloudWatch       /aws/lambda/{CONTACT_FN}
                   /aws/lambda/{GET_FN}

  API Endpoints:
  ─────────────────────────────────────────────
  POST   {api_url}/contact       ← contact form
  GET    {api_url}/submissions   ← read all submissions

  NEXT STEPS:
  1. Verify your email in SES (AWS Console → SES → Verified identities)
  2. Update FROM_EMAIL in lambda/contact_form/lambda_function.py
  3. Test with: curl -X POST {api_url}/contact \\
       -H 'Content-Type: application/json' \\
       -d '{{"name":"Test","email":"you@email.com","message":"Hello"}}'
""")


if __name__ == "__main__":
    role_arn = create_iam_role()
    create_dynamodb_table()
    fn_arns  = deploy_lambda_functions(role_arn)
    api_url  = create_api_gateway(fn_arns)
    create_s3_bucket()
    create_cloudwatch_alarms()
    print_summary(api_url)
