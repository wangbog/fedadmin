<!-- Badges -->
<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/Python-3.12+-yellow.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Flask-3.1.3-green.svg" alt="Flask">
</p>

# FedAdmin

A federated identity management system built with Flask for managing educational and research network organizations, Identity Providers (IdPs), and Service Providers (SPs).

## Quick Start

FedAdmin provides two primary deployment options. Choose the appropriate guide for your needs:

- **Development Environment**: [Development Setup Guide](docs/deployment/deployment_dev.md) - For developers and testing
- **Production Deployment**: [Production Deployment Guide](docs/deployment/deployment_prod.md) - For live systems

After installation, refer to the [User Guide](docs/guides/user_guide.md) for operational instructions.

For detailed documentation, guides, and references, see the [Documentation Index](docs/index.md).

This README provides the project overview. For detailed instructions and guides, please refer to the documentation in the `/docs/` directory.

## Table of Contents

- [Project Overview](#project-overview)
  - [System Organization](#system-organization)
  - [Key Features](#key-features)
  - [Technology Stack](#technology-stack)
  - [Installation Prerequisites](#installation-prerequisites)
- [Storage Management](#storage-management)
  - [Federation Storage](#federation-storage)
  - [Database](#database)
- [SAML Metadata Processing](#saml-metadata-processing)
  - [Metadata Validation](#metadata-validation)
  - [Metadata Transformation](#metadata-transformation)
  - [Metadata Aggregation](#metadata-aggregation)
  - [Referenced Specifications](#referenced-specifications)
- [License](#license)

## Project Overview

FedAdmin is a comprehensive federated identity management system designed for educational and research networks. It provides a centralized platform for managing federation operations, including entity registration, metadata management, and access control across multiple identity providers (IdPs) and service providers (SPs).

### System Organization

The system is organized into two main administrative modules with distinct roles and responsibilities:

#### Federation Administration (`/federation`)
- **User Roles**: `federation` (federation administrator)
- **Permissions**: Full access to all organizations and entities
- **Core Functions**:
  - Entity approval workflow (approve/reject pending applications)
  - Federation metadata aggregation and digital signing
  - Federation configuration and certificate management
  - Member organization management

#### Member Administration (`/member`)
- **User Roles**: `full_member`, `sp_member`
- **Permissions**: Access limited to own organization's data only
- **Core Functions**:
  - Entity lifecycle management (create, edit, delete IdP/SP entities)
  - Metadata validation (XSD schema, structure, entityID uniqueness, scope)
  - Metadata transformation (adding federation-specific extensions)
  - Organization information management
  - User management within organization

| Feature | Member Module | Federation Module |
|---------|---------------|-------------------|
| Create Entity | ✅ | ❌ |
| Edit Entity | ✅ | ❌ |
| Delete Entity | ✅ | ❌ |
| Approve Entity | ❌ | ✅ |
| Reject Entity | ❌ | ✅ |
| Metadata Validation | ✅ | ❌ |
| File Upload Handling | ✅ | ❌ |

### Key Features

- **Multi-role Authentication**: Federation administrators, full member administrators, and SP member administrators with distinct permissions
- **Role-based Access Control**: Granular permissions based on user roles and organization membership
- **Data Isolation**: Strict organization-level data segregation ensuring users can only access their own organization's data
- **SAML Metadata Lifecycle**: Comprehensive validation, transformation, aggregation, and digital signing using pyFF and lxml
- **Entity Approval Workflow**: Two-stage process where members create entities and federation administrators approve them
- **eduGAIN Entity Import**: Support for adding IdP/SP entities that are already part of eduGAIN via another federation. Only the entityID is required - the system automatically retrieves and validates the official metadata directly from eduGAIN's public API.

### Technology Stack

- **Backend Framework**: Flask 3.1.3
- **ORM**: Flask-SQLAlchemy 3.1.1
- **Authentication**: Flask-Security-Too 5.7.1
- **Admin Interface**: Flask-Admin[images] 2.0.2
- **Metadata Aggregation**: pyFF 2.1.5

### Installation Prerequisites

- **Docker and Docker Compose** (required for both development and production)
- **Git** (for repository cloning)

## Storage Management

### Federation Storage

The `storage/` directory is created at runtime and is not included in the project repository via `.gitignore`. Files are automatically organized by organization ID. 

```
storage/
├── public/                            # Public files
│   ├── members/                       # Public member files
│   │   └── {organization_id}/         # Public member files for this member
│   │       └── ...                    # Reserved: public files for this member
│   └── federation/                    # Public federation files
│       ├── federation-metadata.xml    # Production metadata: all approved entities (status = READY)
│       ├── fed-metadata-edugain.xml   # eduGAIN metadata: approved entities with eduGAIN enabled
│       └── fed-metadata-beta.xml      # Beta metadata: entities pending approval (status = INIT or APPROVING)
└── private/                           # Protected files (with access controlled)
    ├── members/                       # Protected member files
    │   └── {organization_id}/         # Protected member files for this member
    │       ├── idp-{idp_id}-metadata.xml              # IdP entity metadata (uploaded by user)
    │       ├── idp-{idp_id}-metadata-transformed.xml  # With federation-specific extensions (e.g., mdui)
    │       ├── sp-{sp_id}-metadata.xml                # SP entity metadata (uploaded by user)
    │       ├── sp-{sp_id}-metadata-transformed.xml    # With federation-specific extensions (e.g., mdui)
    │       └── ...                                    # Other private files for this member
    └── federation/                    # Protected federation files
        ├── fed.crt                    # X.509 certificate (share for signature verification)
        └── fed.key                    # Private key (SECRET - never share, keep permissions restricted)
```

> **⚠️ Security Warning:** The private key (`fed.key`) is critical for signing federation metadata. Ensure it is stored securely with restricted permissions (600) and never exposed to unauthorized users. If compromised, regenerate certificates immediately using `flask init-certs`.

### Database

The application uses SQLite for data storage:

- **Development**: `./instance/fedadmin.db` (host) ↔ `/app/instance/fedadmin.db` (container)
- **Production**: `./instance/fedadmin-prod.db` (host) ↔ `/app/instance/fedadmin-prod.db` (container)

> **⚠️ Important:** The `flask init-db` command will delete all existing data. Use with caution!

## SAML Metadata Processing

The system implements comprehensive SAML metadata lifecycle management, including validation, transformation, and aggregation. All operations comply with SAML 2.0 specifications and REFEDS interoperability profiles.

### Metadata Validation

When an IdP or SP metadata file is uploaded, the system performs the following validation steps:

1. **File Validation**
   - Check for empty files
   - Validate MIME type (XML for metadata files)

2. **XML Structure Validation**
   - Parse XML and verify well-formedness
   - Ensure exactly one `EntityDescriptor` element (reject `EntitiesDescriptor`)
   - Validate root element is `EntityDescriptor`

3. **XSD Schema Validation**
   - Validate against [SAML 2.0 Metadata Schema](https://www.oasis-open.org/committees/download.php/35391/sstc-saml-metadata-errata-2.0-wd-04-diff.pdf)
   - Validate against [Shibboleth Metadata Schema](https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPIdPConfiguration) (if applicable)
   - Additional schemas: XML Signature, XML Encryption

4. **SSO Descriptor Validation**
   - IdP: Must contain `IDPSSODescriptor`
   - SP: Must contain `SPSSODescriptor`

5. **EntityID Validation**
   - Extract `entityID` attribute from `EntityDescriptor`
   - Verify format (must start with `http://`, `https://`, or `urn:`)
   - Check uniqueness across the federation database

6. **Scope Validation (IdP only)**
   - Verify `IDPSSODescriptor` contains `Extensions` element
   - Extract and validate `shibmd:Scope` element
   - Check `regexp` attribute is set to `"false"`
   - Validate scope value is a valid domain format

### Metadata Transformation

After validation, the system transforms the uploaded metadata by adding federation-specific extensions:

1. **Registration Information** ([mdrpi:RegistrationInfo](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-rpi/v1.0/sstc-saml-metadata-rpi-v1.0.html))
   - Registration authority (from federation configuration)
   - Registration instant (current timestamp)
   - Registration policy URL(s)

2. **UI Information** ([mdui:UIInfo](https://docs.oasis-open.org/security/SAML/Post2.0/sstc-saml-metadata-ui/v1.0/cos01/sstc-saml-metadata-ui-v1.0.html))
   - Display name (from entity name)
   - Description (from entity description)
   - Logo URL (from stored logo file)
   - Information URL (SP only)
   - Privacy Statement URL (SP only)

3. **Entity Attributes** ([mdattr:EntityAttributes](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-errata-2.0-wd-04-diff.pdf))
   - [REFEDS Research & Scholarship](https://refeds.org/category/research-and-scholarship) (R&S) category
   - [REFEDS Code of Conduct](https://refeds.org/category/code-of-conduct) (CoCo) - SP only
   - [REFEDS Sirtfi Framework](https://refeds.org/sirtfi) (Security Incident Response Trust Framework for Federated identity)

4. **Organization Information** ([md:Organization](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-errata-2.0-wd-04-diff.pdf))
   - Organization name
   - Organization URL
   - Organization display name

5. **Contact Persons** ([md:ContactPerson](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-errata-2.0-wd-04-diff.pdf))
   - Technical contact (name and email)
   - Security contact (for Sirtfi-compliant entities)

6. **Scope Element** (IdP only)
   - Ensure `shibmd:Scope` is present and matches the validated scope

The transformed metadata is saved as `{original-filename}-transformed.xml`.

### Metadata Aggregation

The system regenerates the federation metadata aggregate both on-demand and on a scheduled basis:

#### Asynchronous Regeneration

When entities are created, updated, or deleted through the admin interface, the system automatically triggers an asynchronous metadata regeneration task. This ensures that:

- User requests are not blocked by the time-consuming metadata generation process
- The beta metadata (for pending entities) is updated promptly
- Multiple rapid changes are coalesced into a single regeneration task

The async regeneration uses APScheduler's background scheduler with the following features:
- `replace_existing=True`: Prevents task accumulation when multiple changes occur rapidly
- `misfire_grace_time=60`: Allows up to 60 seconds delay before skipping a task

#### Scheduled Tasks

For detailed information about the system's scheduled tasks, including daily metadata regeneration and eduGAIN synchronization, please refer to the [Scheduled Tasks Guide](docs/guides/scheduled_tasks.md). This document provides comprehensive documentation on configuration, processes, and troubleshooting.

The scheduled tasks include:
- Daily metadata regeneration to maintain compliance with eduGAIN requirements
- Hourly monitoring of entities already in eduGAIN

#### Configuration

The metadata regeneration behavior can be customized via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `METADATA_REGENERATION_TIME` | Time to run daily metadata regeneration (UTC). Format: "hour:minute" (e.g., "2:00") | `2:00` |
| `METADATA_REGENERATION_MISFIRE_GRACE_TIME` | Grace time (in seconds) for async metadata regeneration tasks before they are skipped | `60` |

For more configuration options, see the [Scheduled Tasks Guide](docs/guides/scheduled_tasks.md).

### Referenced Specifications

| Specification | Description |
|---------------|-------------|
| [SAML V2.0 Metadata](https://www.oasis-open.org/committees/download.php/35391/sstc-saml-metadata-errata-2.0-wd-04-diff.pdf) | Core SAML 2.0 metadata specification |
| [SAML V2.0 Metadata Interoperability Profile](https://docs.oasis-open.org/security/SAML/Post2.0/sstc-saml-metadata-iop/v1.0/sstc-saml-metadata-iop-v1.0.html) | Interoperability guidelines for SAML metadata |
| [REFEDS Sirtfi Framework](https://refeds.org/sirtfi) | Security Incident Response Trust Framework for Federated identity |
| [REFEDS Research & Scholarship](https://refeds.org/category/research-and-scholarship) | Entity category for research and scholarship collaboration |
| [REFEDS Code of Conduct](https://refeds.org/category/code-of-conduct) | Data protection and privacy guidelines for service providers |
| [Shibboleth Metadata Profile](https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPIdPConfiguration) | Shibboleth-specific metadata extensions |
| [XML-Signature Syntax and Processing](https://www.w3.org/TR/xmldsig-core/) | W3C standard for XML digital signatures |
| [mdrpi:RegistrationInfo](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-rpi/v1.0/sstc-saml-metadata-rpi-v1.0.html) | SAML Metadata Registration Information |
| [mdui:UIInfo](https://docs.oasis-open.org/security/SAML/Post2.0/sstc-saml-metadata-ui/v1.0/cos01/sstc-saml-metadata-ui-v1.0.html) | SAML Metadata User Interface Extension |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Documentation

For complete documentation, refer to:
- [Documentation Index](docs/index.md) - Overview of all documentation
- [User Guide](docs/guides/user_guide.md) - Comprehensive user documentation
- [Scheduled Tasks](docs/guides/scheduled_tasks.md) - System automation and maintenance tasks
- [Development Setup](docs/deployment/deployment_dev.md) - Development environment setup
- [Production Deployment](docs/deployment/deployment_prod.md) - Production deployment guide
- [Known Issues](docs/reference/issues.md) - Current known issues and limitations
- [Backlog](docs/reference/backlog.md) - Future improvements and planned features
- [Glossary](docs/reference/glossary.md) - Federation terminology and definitions

## Support

If you encounter any issues or have questions:
1. Check the [Known Issues](docs/reference/issues.md) document
2. Review the troubleshooting section in the [Development Setup Guide](docs/deployment/deployment_dev.md#troubleshooting)
3. Create an issue on GitHub with detailed information about your problem