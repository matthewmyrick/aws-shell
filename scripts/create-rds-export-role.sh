#!/bin/bash
set -euo pipefail

ROLE_NAME="rds-s3-export-role"
POLICY_NAME="rds-s3-export-policy"
BUCKET_NAME="hadrius-testing-resources"
KMS_KEY_ID="f52f1c5d-f86f-46a9-ab03-d05dcf9c3f88"
ACCOUNT_ID="748201795369"
REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")

echo "Creating IAM role: ${ROLE_NAME}"
echo "  Bucket:  ${BUCKET_NAME}"
echo "  KMS Key: ${KMS_KEY_ID}"
echo "  Region:  ${REGION}"
echo ""

# Step 1: Create the role with trust policy for RDS export service
aws iam create-role \
  --role-name "${ROLE_NAME}" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "export.rds.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

echo ""
echo "Role created. Attaching permissions policy..."

# Step 2: Attach inline policy with S3 + KMS permissions
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "${POLICY_NAME}" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": [
          \"s3:PutObject\",
          \"s3:GetObject\",
          \"s3:ListBucket\",
          \"s3:DeleteObject\",
          \"s3:GetBucketLocation\",
          \"s3:AbortMultipartUpload\"
        ],
        \"Resource\": [
          \"arn:aws:s3:::${BUCKET_NAME}\",
          \"arn:aws:s3:::${BUCKET_NAME}/exports/*\"
        ]
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [
          \"kms:Encrypt\",
          \"kms:Decrypt\",
          \"kms:ReEncryptFrom\",
          \"kms:ReEncryptTo\",
          \"kms:GenerateDataKey\",
          \"kms:GenerateDataKeyWithoutPlaintext\",
          \"kms:DescribeKey\",
          \"kms:CreateGrant\",
          \"kms:RetireGrant\"
        ],
        \"Resource\": \"arn:aws:kms:${REGION}:${ACCOUNT_ID}:key/${KMS_KEY_ID}\"
      }
    ]
  }"

echo ""
echo "Done! Role ARN:"
echo "  arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo ""
echo "Use it with:"
echo "  aws rds start-export-task \\"
echo "    --export-task-identifier my-export \\"
echo "    --source-arn <snapshot-arn> \\"
echo "    --s3-bucket-name ${BUCKET_NAME} \\"
echo "    --s3-prefix exports/ \\"
echo "    --iam-role-arn arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME} \\"
echo "    --kms-key-id ${KMS_KEY_ID}"
