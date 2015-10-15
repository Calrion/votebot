#!/bin/bash

# Uses the AWS CLI and jq to create an IAM role for votebot

role_name=votebotcli
policy_name=votebot-policycli

# Create the role
aws iam create-role --role-name $role_name --assume-role-policy-document file://votebot-role.json

# Create the policy
policy_arn=$(aws iam create-policy --policy-name $policy_name --policy-document file://votebot-policy.json | jq -r '.Policy.Arn')

# Attach the role to the policy
aws iam attach-role-policy --role-name $role_name --policy-arn $policy_arn
