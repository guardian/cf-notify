#!/usr/bin/env bash

if [ $# -lt 1 ]
then
    echo "usage: deploy.sh <ENV> <BUCKET> <WEBHOOK> [CHANNEL]"
    exit 1
fi

ENV=$1
BUCKET=$2
WEBHOOK=$3
CHANNEL=$4

if [ -z $ENV ];
then
    echo "Please specify an environment.";
    exit 1
fi

if [ -z $BUCKET ];
then
    echo "Please specify a destination bucket";
    exit 1
fi

if [ -z $WEBHOOK ];
then
    echo "Please specify a Slack WebHook";
    exit 1
fi

cat > slack.py <<EOL
WEBHOOK='$WEBHOOK'
CHANNEL='$CHANNEL'
EOL

zip cf-notify.zip lambda_notify.py slack.py
aws s3 cp cf-notify.zip s3://$BUCKET/cf-notify-$ENV.zip

rm slack.py
rm cf-notify.zip
