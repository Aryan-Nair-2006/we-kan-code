# Atlas Knowledge Platform — Incident Post-Mortem (INC-402)

**Document ID**: DOC-ATLAS-INC-07  
**Version**: 1.0  
**Owner**: SRE Core  
**Access Level**: team  
**Status**: ACTIVE  

## 1. Summary
On November 14, 2026, OpenSearch Serverless collection experienced elevated vector query latency due to an overly restrictive VPC security group rule.

## 2. Root Cause
The security group rule blocked port 443 egress traffic from QueryLambda to the collection endpoint during peak load.

## 3. Resolution
The security group was updated to permit HTTPS egress to the OpenSearch Serverless endpoint, restoring normal 250ms query latencies.
