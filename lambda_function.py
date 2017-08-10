'''
The MIT License (MIT)

Copyright (c) 2016 Benjamin D. Jones

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import base64
import uuid
import httplib
import urlparse
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def send_response(request, response, status=None, reason=None):
    """ Send our response to the pre-signed URL supplied by CloudFormation

    If no ResponseURL is found in the request, there is no place to send a
    response. This may be the case if the supplied event was for testing.
    """

    if status is not None:
        response['Status'] = status

    if reason is not None:
        response['Reason'] = reason

    if 'ResponseURL' in request and request['ResponseURL']:
        url = urlparse.urlparse(request['ResponseURL'])
        body = json.dumps(response)
        https = httplib.HTTPSConnection(url.hostname)
        https.request('PUT', url.path+'?'+url.query, body)

    return response


def lambda_handler(event, context):
    logger.info('got event RequestType={}'.format(event['RequestType']))

    response = {
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Status': 'SUCCESS'
    }

    # PhysicalResourceId is meaningless here, but CloudFormation requires it
    if 'PhysicalResourceId' in event:
        response['PhysicalResourceId'] = event['PhysicalResourceId']
    else:
        response['PhysicalResourceId'] = str(uuid.uuid4())

    # There is nothing to do for a delete request
    if event['RequestType'] == 'Delete':
        return send_response(event, response)

    # Encrypt the value using AWS KMS and return the response
    try:

        for key in ['KeyId', 'PlainText']:
            if key not in event['ResourceProperties'] or not event['ResourceProperties'][key]:
                return send_response(
                    event, response, status='FAILED',
                    reason='The properties KeyId and PlainText must not be empty'
                )

        client = boto3.client('kms')
        encrypted = client.encrypt(
            KeyId=event['ResourceProperties']['KeyId'],
            Plaintext=event['ResourceProperties']['PlainText']
        )

        response['Data'] = {
            'CipherText': base64.b64encode(encrypted['CiphertextBlob'])
        }
        response['Reason'] = 'The value was successfully encrypted'

    except Exception as E:
        logger.exception(E)
        response['Status'] = 'FAILED'
        response['Reason'] = 'Encryption Failed - See CloudWatch logs for the Lambda function backing the custom resource for details'

    return send_response(event, response)
