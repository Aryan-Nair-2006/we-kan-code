# Atlas Knowledge Platform — Deployment Runbook

**Document ID**: DOC-ATLAS-OPS-04  
**Version**: 1.2  
**Owner**: DevOps & Infrastructure Team  
**Access Level**: developer  
**Status**: ACTIVE  

## 1. Deployment Schedule
Production deployments are scheduled strictly on Tuesday at 03:00 UTC to minimize user impact across global time zones.

## 2. Infrastructure as Code (SAM)
The deployment pipeline uses AWS Serverless Application Model (SAM):
1. Build preparation: `python scripts/prepare_sam_build.py`
2. Template validation: `sam validate -t infrastructure/template.yaml --lint`
3. Function packaging: `sam build -t infrastructure/template.yaml`
4. CloudFormation deployment: `sam deploy`

## 3. Supported Region
The primary production region is `ap-south-1` (Mumbai).
