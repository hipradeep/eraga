# Production Deployment Policy

## 1. Scope

This policy governs all deployments to production environments across staging and
production regions. It applies to application services, database migrations, and
infrastructure changes.

## 2. Change Approval

Production deployments require written sign-off from the Release Manager and at
least two senior engineers holding the Senior or Staff engineering grade. No
single individual may approve their own change.

## 3. Change Window

Standard deployments are permitted only during the approved change window of
Tuesday to Thursday, 10:00 to 16:00 local time. Deployments outside the change
window require Director-level approval and must be accompanied by a documented
rollback plan.

## 4. Emergency Changes

Emergency fixes for severity 1 production incidents may bypass the standard review
cycle with VP-level approval. The change must be applied by two engineers, and a
post-incident review document must be filed within 5 business days.

## 5. Database Migrations

Database migrations must be backward compatible and reversible. Migrations that
drop or rename a column must be deployed in two stages across separate releases.
The on-call database engineer must approve any migration touching more than 10000
rows.

## 6. Rollback

Every deployment must have a tested rollback path documented in the change
record. The on-call engineer retains the authority to roll back any deployment
that causes customer impact, without seeking further approval.

## 7. Verification

After each production deployment the deploying engineer must verify application
health endpoints, error rates, and latency percentiles for 30 minutes before
closing the change record.