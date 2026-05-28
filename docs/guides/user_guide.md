# User Guide

This document provides comprehensive guidance for users of the FedAdmin federated identity management system. It covers user roles, operational workflows, and system features.

## Table of Contents

1. [User Roles](#user-roles)
2. [Federation Initial Setup Process](#federation-initial-setup-process)
3. [Member Organizations and Users Management](#member-organizations-and-users-management)
4. [Current Member Organization and Users Management](#current-member-organization-and-users-management)
5. [Identity Provider Management](#identity-provider-management)
6. [Service Provider Management](#service-provider-management)
7. [Note on Metadata Files](#note-on-metadata-files)

## User Roles

The FedAdmin system defines two primary administrative categories with distinct permissions and responsibilities. For detailed information about these roles, please refer to the [project README documentation](../../README.md#system-organization).

**Note**: Users under the `FEDERATION_ADMIN` organization (which is unique) have both federation administrator and full member administrator privileges. After login, users can switch between identities using the "Site/Switch to Member(Federation) Admin" link.

## Federation Initial Setup Process

**Required Role**: Federation Administrator

### 2.1 Change Password
- Navigate to `Site/Change Password` page
- The initial federation administrator created during deployment receives a randomly generated password from `flask init-db`
- Change this deployment password after first login
- This is a critical security requirement for protecting federation administrative access

### 2.2 Complete Federation Information
- Navigate to `Federation Admin/Federation` page
- Complete the following information about your federation:
  - Registration Authority
  - Registration Policy URL
  - Publisher information
- This information will be used when generating federation metadata files (`mdrpi`)
  - Reference: [SAML V2.0 Metadata Extensions for Registration and Publication Information](https://docs.oasis-open.org/security/saml/Post2.0/saml-metadata-rpi/v1.0/saml-metadata-rpi-v1.0.pdf)
- All federation administrators should ensure these details are accurate and complete before proceeding with entity registration

## Member Organizations and Users Management

**Note**: The current business flow requires Federation Administrators to manually register Organizations and Users. Organizations must be created first by the Federation Administrator, followed by Users who are then assigned to these Organizations. This process is not designed for self-service registration by users.

**Required Role**: Federation Administrator

### 3.1 Manage Member Organizations
- Navigate to `Federation Admin/Organization` page
- **Organization Types**:
  - `FULL_MEMBER`: Can create and manage both IdP and SP entities
  - `SP_MEMBER`: Can only create and manage SP entities
- **Note**: Only these organization types can be created; `FEDERATION_ADMIN` is automatically created during initialization
- **Organization Status Field**: 
  - This is a reserved field with no active functionality at present
  - It is recommended to set this field to `READY` for all organizations
  - Future development may implement registration/approval logic based on this status field, potentially supporting a multi-stage approval workflow (e.g., PENDING → APPROVED → READY)
  - This would allow for more granular control over organization lifecycle management

### 3.2 Manage Users
- Navigate to `Federation Admin/User` page
- Create new users and assign them to specific organizations
- Each user must be associated with an organization before they can be created
- Users will receive appropriate roles based on their organization type
- When a user is created, the system generates a password setup/reset link
- The system attempts to email the link to the new user
- The link is also shown once on the page for the administrator to copy if needed
- Email delivery status can be reviewed in `Federation Admin/System/Email Delivery`
- Do not send or reuse predictable temporary passwords

## Current Member Organization and Users Management

**Note**: Users can only manage their own organization's data and users within their assigned organization.

**Required Roles**: Full Member Administrator / SP Member Administrator

### 4.1 Change Password
- Navigate to `Site/Change Password` page
- New organization users normally set their password through the setup/reset link created by their administrator
- Users can later change their own password from this page
- This is a critical security requirement for protecting administrative access

### 4.2 Complete Organization Information
- Navigate to `Member Admin/Organization` page
- Complete the following information about your organization:
  - Description
  - URL
  - Display name (if applicable)
- This information will be used when generating federation metadata files (`md:Organization`)
  - Reference: [SAML V2.0 Metadata](https://docs.oasis-open.org/security/saml/v2.0/saml-metadata-2.0-os.pdf)
- All member administrators should ensure these details are accurate and complete before proceeding with entity registration

### 4.3 Manage Organization Users
- Navigate to `Member Admin/User` page
- Manage users within your current organization
- Create, edit, or delete users as needed
- Assign appropriate roles based on your current organization type
- When a user is created, the system generates a password setup/reset link
- The system attempts to email the link to the new user
- The link is also shown once on the page for the administrator to copy if needed
- Email delivery status can be reviewed by federation administrators in `Federation Admin/System/Email Delivery`

## Identity Provider Management

### 5.1 Create/Modify IdP (Full Member Administrators)
- Navigate to `Member Admin/IdP` page
- **IdP eduGAIN Status Options**:
  - `ALREADY_IN`: No metadata file upload required. Only EntityID is needed; the system will automatically retrieve metadata from eduGAIN's API
  - Other options: Metadata file upload is mandatory
- Created IdP entities have `INIT` status by default
- Ensure all required fields are completed before submission

### 5.2 Submit for Approval (Full Member Administrators)
- Navigate to `Member Admin/IdP` page
- Click "Submit for approval" button
- IdP entity status changes from `INIT` to `APPROVING`
- Submission requires a current transformed metadata file. If the transformed metadata is missing or outdated, edit and save the entity first, then submit it again.
- **Note**: IdP entities in `APPROVING` status can be withdrawn back to `INIT` status using the "Cancel application" button

### 5.3 Approve/Reject (Federation Administrators)
- Navigate to `Federation Admin/IdP` page
- Click "Approve" or "Reject" buttons as appropriate
- Approved IdP entities change status to `READY`
- Rejected IdP entities return to `INIT` status

### 5.4 Withdraw (Full Member Administrators)
- Navigate to `Member Admin/IdP` page
- READY status IdP entities can be withdrawn using the "Withdraw" button
- Withdrew IdP entities return to `INIT` status

## Service Provider Management

Service Provider management follows the same workflow as Identity Provider Management, with the following differences:

- **Eligible Roles**: Both Full Member Administrators and SP Member Administrators can manage Service Providers
- **Navigation**: Access through `Member Admin/SP` page instead of `Member Admin/IdP`
- **SP-specific Options**: SP entities have eduGAIN status options similar to IdP entities, but the metadata file requirements and validation rules are specific to Service Provider configurations

All other aspects of the workflow (creation, submission for approval, approval/rejection by federation administrators, and withdrawal) follow the same procedures as described in the Identity Provider Management section.

## Note on Metadata Files

The following applies to both Identity Provider and Service Provider management:

- `INIT` and `APPROVING` status IdP/SP entities are included in `fed-metadata-beta.xml` for testing and validation
- `READY` status IdP/SP entities are included in `fed-metadata.xml` for production use
- `READY` status IdP/SP entities with `idp_edugain` or `sp_edugain` set to `YES` are also included in `fed-metadata-edugain.xml`, which serves as the federation's metadata feed for eduGAIN
- When an entity is created or edited, FedAdmin transforms its metadata before regenerating beta metadata. If transformation fails, the entity is saved but beta metadata is not regenerated until the metadata issue is corrected and the entity is saved again.
