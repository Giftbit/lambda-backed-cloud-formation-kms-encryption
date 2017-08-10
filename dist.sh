#!/usr/bin/env bash

BUCKET="giftbit-public-resources"
KEY_PREFIX="cloudformation/lambda-backed-cloud-formation-kms-encryption/lambda"

set -eu

zip dist *.template *.py *.md LICENSE
aws s3 cp ./dist.zip s3://$BUCKET/$KEY_PREFIX/`date +%Y%m%d-%H%M`.zip --acl public-read
