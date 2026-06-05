# Administrator Guide

This document provides guidance for FedAdmin administrators: federation administrators and member organization administrators. It does not describe end-user workflows for students, faculty, researchers, or other people who authenticate through the federation.

## Table of Contents

1. [Administrator Roles](#administrator-roles)
2. [Federation Initial Setup Process](#federation-initial-setup-process)
3. [Member Organizations and Administrators Management](#member-organizations-and-administrators-management)
4. [Member Organization Administrators Management](#member-organization-administrators-management)
5. [Identity Provider Management](#identity-provider-management)
6. [Service Provider Management](#service-provider-management)
7. [Note on Metadata Files](#note-on-metadata-files)

## Administrator Roles

The FedAdmin system defines two primary administrative categories with distinct permissions and responsibilities. For detailed information about these roles, please refer to the [project README documentation](../../README.md#core-concepts).

**Note**: Administrators under the `FEDERATION_ADMIN` organization (which is unique) have both Federation Administrator and Full Member Administrator privileges. After login, they can switch between identities using the "Site/Switch to Member(Federation) Admin" link.

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

## Member Organizations and Administrators Management

**Note**: In FedAdmin, "Users" refers to users of this system: administrator accounts for Federation Administrators or member organizations. It does not mean end users such as students, faculty, or researchers who authenticate through the federation. The current business flow requires Federation Administrators to manually register Organizations and administrators. Organizations must be created first by the Federation Administrator, followed by one or more administrators assigned to each Organization. This process is not designed for self-service registration by member organizations or end users.

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
  - Future development may implement registration/approval logic based on this status field, potentially supporting a multi-stage approval workflow (e.g., PENDING -> APPROVED -> READY)
  - This would allow for more granular control over organization lifecycle management

### 3.2 Manage Users
- Navigate to `Federation Admin/User` page
- Create new administrator accounts and assign them to specific organizations
- Each administrator must be associated with an organization before they can be created
- One organization can have multiple administrators
- Administrators receive appropriate roles based on their organization type
- When a user is created, the system generates a password setup/reset link
- The system attempts to email the link to the new user
- The link is also shown once on the page for the administrator to copy if needed
- Treat this link as credential-equivalent. Share it only with the intended user through a trusted channel, and do not paste it into screenshots, tickets, chat logs, or public issues
- Email delivery status can be reviewed in `Federation Admin/System/Email Delivery`
- Do not send or reuse predictable temporary passwords

## Member Organization Administrators Management

**Note**: Member administrators can only manage their own organization's data and administrators within their assigned organization. One organization can have multiple administrators.

**Required Roles**: Full Member Administrator / SP Member Administrator

### 4.1 Change Password
- Navigate to `Site/Change Password` page
- New organization administrators normally set their password through the setup/reset link created by their administrator
- Administrators can later change their own password from this page
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
- Manage administrator accounts within your current organization
- Create, edit, or delete administrators as needed
- Assign appropriate roles based on your current organization type
- When a user is created, the system generates a password setup/reset link
- The system attempts to email the link to the new user
- The link is also shown once on the page for the administrator to copy if needed
- Treat this link as credential-equivalent. Share it only with the intended user through a trusted channel, and do not paste it into screenshots, tickets, chat logs, or public issues
- Email delivery status can be reviewed by federation administrators in `Federation Admin/System/Email Delivery`

## Identity Provider Management

### 5.1 Create/Modify IdP (Full Member Administrators)
- Navigate to `Member Admin/IdP` page
- **IdP eduGAIN Status Options**:
  - `YES`: Include this IdP in the federation's eduGAIN metadata output after it is approved. Metadata file upload is mandatory.
  - `NO`: Do not include this IdP in the federation's eduGAIN metadata output. It can still be included in beta and production federation metadata. Metadata file upload is mandatory.
  - `ALREADY_IN`: The IdP entity has already been added to eduGAIN through another federation. No metadata file upload is required. Only EntityID is needed; the system will automatically retrieve metadata from eduGAIN's API
- Created IdP entities have `INIT` status by default
- Ensure all required fields are completed before submission

### 5.2 Submit for Approval (Full Member Administrators)
- Navigate to `Member Admin/IdP` page
- Click "Submit for approval" button
- IdP entity status changes from `INIT` to `APPROVING`
- **Note**: IdP entities in `APPROVING` status can be withdrawn back to `INIT` status using the "Cancel application" button

### 5.3 Approve/Reject (Federation Administrators)
- Navigate to `Federation Admin/IdP` page
- Click "Approve" or "Reject" buttons as appropriate
- Approved IdP entities change status to `READY`
- Rejected IdP entities return to `INIT` status

### 5.4 Withdraw (Full Member Administrators)
- Navigate to `Member Admin/IdP` page
- READY status IdP entities can be withdrawn using the "Withdraw" button
- Withdrawn IdP entities return to `INIT` status

## Service Provider Management

Service Provider management follows the same workflow as Identity Provider Management, with the following differences:

- **Eligible Roles**: Both Full Member Administrators and SP Member Administrators can manage Service Providers
- **Navigation**: Access through `Member Admin/SP` page instead of `Member Admin/IdP`
- **SP-specific Validation**: Metadata validation rules are specific to Service Provider configurations.

All other aspects of the workflow (creation, submission for approval, approval/rejection by federation administrators, and withdrawal) follow the same procedures as described in the Identity Provider Management section.

## Note on Metadata Files

The following applies to both Identity Provider and Service Provider management:

- `INIT` and `APPROVING` status IdP/SP entities are included in `fed-metadata-beta.xml` for testing and validation
- `READY` status IdP/SP entities are included in `fed-metadata.xml` for production use
- `READY` status IdP/SP entities whose eduGAIN participation option was explicitly set to `YES` are also included in `fed-metadata-edugain.xml`, which serves as the federation's metadata feed for eduGAIN
- When an entity is created or edited, FedAdmin transforms its metadata before regenerating beta metadata. If transformation fails, the entity is saved but beta metadata is not regenerated until the metadata issue is corrected and the entity is saved again.
- If production metadata cannot be regenerated during approval or withdrawal, the status change is not completed. Follow the on-screen guidance, then retry after the metadata generation issue is fixed.
