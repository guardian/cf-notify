import json
import shlex
import urllib
import urllib2
import slack
import boto3
import re
from itertools import groupby

# Mapping CloudFormation status codes to colors for Slack message attachments
# Status codes from http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-describing-stacks.html
STATUS_COLORS = {
    'CREATE_COMPLETE': 'good',
    'CREATE_IN_PROGRESS': 'good',
    'CREATE_FAILED': 'danger',
    'DELETE_COMPLETE': 'good',
    'DELETE_FAILED': 'danger',
    'DELETE_IN_PROGRESS': 'good',
    'ROLLBACK_COMPLETE': 'warning',
    'ROLLBACK_FAILED': 'danger',
    'ROLLBACK_IN_PROGRESS': 'warning',
    'UPDATE_COMPLETE': 'good',
    'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS': 'good',
    'UPDATE_IN_PROGRESS': 'good',
    'UPDATE_ROLLBACK_COMPLETE': 'warning',
    'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS': 'warning',
    'UPDATE_ROLLBACK_FAILED': 'danger',
    'UPDATE_ROLLBACK_IN_PROGRESS': 'warning'
}

# List of CloudFormation status that will trigger a call to `get_stack_summary_attachment`
DESCRIBE_STACK_STATUS = [
    'CREATE_COMPLETE',
    'DELETE_IN_PROGRESS'
]

# List of properties from ths SNS message that will be included in a Slack message
SNS_PROPERTIES_FOR_SLACK = [
    'Timestamp',
    'StackName',
]


def lambda_handler(event, context):
    message = event['Records'][0]['Sns']
    sns_message = message['Message']
    cf_message = dict(token.split('=', 1) for token in shlex.split(sns_message))

    # ignore messages that do not pertain to the Stack as a whole
    if not cf_message['ResourceType'] == 'AWS::CloudFormation::Stack':
        return

    message = get_stack_update_message(cf_message)
    data = json.dumps(message)
    req = urllib2.Request(slack.WEBHOOK, data, {'Content-Type': 'application/json'})
    urllib2.urlopen(req)


def get_stack_update_message(cf_message):
    attachments = [
        get_stack_update_attachment(cf_message)
    ]

    if cf_message['ResourceStatus'] in DESCRIBE_STACK_STATUS:
        attachments.append(get_stack_summary_attachment(cf_message['StackName']))

    stack_url = get_stack_url(cf_message['StackId'])

    message = {
        'icon_emoji': ':cloud:',
        'username': 'cf-bot',
        'text': 'Stack: {stack} has entered status: {status} <{link}|(view in web console)>'.format(
                stack=cf_message['StackName'], status=cf_message['ResourceStatus'], link=stack_url),
        'attachments': attachments
    }

    if slack.CHANNEL:
        message['channel'] = slack.CHANNEL

    return message


def get_stack_update_attachment(cf_message):
    title = 'Stack {stack} is now status {status}'.format(
        stack=cf_message['StackName'],
        status=cf_message['ResourceStatus'])

    return {
        'fallback': title,
        'title': title,
        'fields': [{'title': k, 'value': v, 'short': True}
                   for k, v in cf_message.iteritems() if k in SNS_PROPERTIES_FOR_SLACK],
        'color': STATUS_COLORS.get(cf_message['ResourceStatus'], '#000000'),
    }


def get_stack_summary_attachment(stack_name):
    client = boto3.client('cloudformation')
    resources = client.describe_stack_resources(StackName=stack_name)
    sorted_resources = sorted(resources['StackResources'], key=lambda res: res['ResourceType'])
    grouped_resources = groupby(sorted_resources, lambda res: res['ResourceType'])
    resource_count = {key: len(list(group)) for key, group in grouped_resources}

    title = 'Breakdown of all {} resources'.format(len(resources['StackResources']))

    return {
        'fallback': title,
        'title': title,
        'fields': [{'title': 'Type {}'.format(k), 'value': 'Total {}'.format(v), 'short': True}
                   for k, v in resource_count.iteritems()]
    }


def get_stack_region(stack_id):
    regex = re.compile('arn:aws:cloudformation:(?P<region>[a-z]{2}-[a-z]{4,9}-[1-2]{1})')
    return regex.match(stack_id).group('region')


def get_stack_url(stack_id):
    region = get_stack_region(stack_id)

    query = {
        'filter': 'active',
        'tab': 'events',
        'stackId': stack_id
    }

    return ('https://{region}.console.aws.amazon.com/cloudformation/home?region={region}#/stacks?{query}'
            .format(region=region, query=urllib.urlencode(query)))
