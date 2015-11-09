# CF Notify

## What?
An AWS Lambda function that will post Cloud Formation status updates to a Slack channel via a Slack Web Hook.


## Why?
To give visibility of Cloud Formation changes to the whole team in a quick and simple manner. For example:

![example Slack messages](./example.jpeg)


## How?
CF Notify has a stack of AWS resources consisting of:
 - An SNS Topic
 - A Lambda function, which uses the SNS Topic as an event source
 - An IAM Role to execute the Lambda function

We add the SNS Topic of CF Notify to the notification ARNs of the Stack we want to monitor.
Search for `NotificationARNs.member.N` [here](http://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_UpdateStack.html)
for more information on notification ARNs.


## Setup

To setup CF Notify, we need to do the following.

### Prerequisites

CF Notify has two prerequisites: a S3 Bucket and a Slack incoming webhook.

#### S3 Bucket
You can use a pre-existing bucket in your account, however, to maintain isolation, it's generally best to create a bucket:

```sh
BUCKET="cf-notify-`pwgen -1 --no-capitalize 20`"
aws s3 mb "s3://$BUCKET"
```

#### Slack incoming webhook
You can create an incoming webhook [here](https://my.slack.com/services/new/incoming-webhook/).


### Deploy Lambda

This is done using the script [deploy.sh](./deploy.sh).

```sh
./deploy.sh $ENV $BUCKET $WEBHOOK [$CHANNEL]
```

Where:
 - ENV is the environment of the Stack we are monitoring, e.g. DEV, TEST, PROD. It will be used in the naming of the Lambda artifact file stored in S3.
 - BUCKET is the S3 bucket to store the Lambda artifact.
 - WEBHOOK is the Web Hook URL of an Incoming Web Hook (see https://api.slack.com/incoming-webhooks).
 - CHANNEL is optional and is the Slack channel or user to send messages to. Defaults to the channel chosen when the webhook was created.

If you don't want to send messages to the channel of the webhook, set `$CHANNEL` as another channel or user. For example `#general` or `@foo`.
This is useful if you want to setup CF Notify for your own DEV stack. In this case, you'd want to set `$ENV` as your AWS IAM name:

```sh
ENV="DEV-`aws iam get-user | jq '.User.UserName' | tr -d '"'`"
```

`deploy.sh` will create a zip file and upload it to `s3://$BUCKET/cf-notify-$ENV.zip`.


### Create CF Notify Stack

Create a Stack using the [template](./cf-notify.json).

```sh
aws cloudformation create-stack --template-body file://cf-notify.json \
    --stack-name cf-notify-$ENV \
    --capabilities CAPABILITY_IAM \
    --parameters ParameterKey=Bucket,ParameterValue=$BUCKET ParameterKey=Environment,ParameterValue=$ENV
```

## Usage

Once setup is complete, all you need to do now is set the notification ARN when you update your Cloud Formation stack:

```sh
SNS_ARN=`aws cloudformation describe-stacks --stack-name cf-notify-$ENV | jq ".Stacks[].Outputs[].OutputValue"  | tr -d '"'`

aws cloudformation [create-stack|update-stack|delete-stack] --notification-arns $SNS_ARN
```

You should now see messages in Slack!
