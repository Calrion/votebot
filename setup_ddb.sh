#!/bin/bash

# Uses the AWS CLI and to create tables for votebot

aws dynamodb create-table --table-name vote-options2 --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1 --key-schema AttributeName=selection,KeyType=HASH --attribute-definitions AttributeName=selection,AttributeType=S

aws dynamodb create-table --table-name vote-open2 --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1 --key-schema AttributeName=vote,KeyType=HASH --attribute-definitions AttributeName=vote,AttributeType=S
