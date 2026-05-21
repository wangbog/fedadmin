<!-- Badges -->
<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/Python-3.12+-yellow.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Flask-3.1.3-green.svg" alt="Flask">
</p>

# FedAdmin

A web based management tool for NREN identity federation administrators to operate federations, managing Identity Providers (IdPs) and Service Providers (SPs), and exchanging metadata with eduGAIN metadata service.

## 1. About FedAdmin

### Project Background

We are the **CARSI** team, which manages China's NREN Identity Federation. 

The China Education and Research Computer Network Federated Authentication and Resource Sharing Infrastructure (**CARSI**) provides federal authentication and global academic information resource sharing services for universities and research institutions that have established unified identity authentication on campus networks. CARSI joined eduGAIN in 2019 and over the years we have accumulated extensive experience in managing federations. 

Based on this practical experience, we decided to share our knowledge and tools through this open-source project. (For more information about CARSI, please refer to https://www.carsi.edu.cn)

### Who/When/Why Use FedAdmin

**Who**: Federation administrators who are responsible for managing their NREN's identity federation.

**When**: Your NREN has already joined or is in the process of joining eduGAIN, and you are now planning a technical tool to manage the federation's IdPs and SPs.

**Why**: 
- This management concept and workflow have been successfully used in CARSI's actual projects for many years
- The system can meet common federation management scenarios and shield the complexity of SAML metadata
- It provides a solution for operating federations and exchanging metadata with eduGAIN metadata service

See [eduGAIN: Join As Federation](https://technical.edugain.org/joining_checklist) for a practical checklist before joining eduGAIN.

### Primary Deliverables

Administrators of NREN‑operated identity federations use this project to manage their federation’s Identity Providers (IdPs) and Service Providers (SPs). The primary deliverables are federation metadata files stored under `./app/storage/public/federation/` (the final host‑side path may vary depending on deployment configuration):

**fed-metadata-beta.xml**: Beta metadata for entities pending approval. This file is ideal for federations that wish to maintain a separate test environment to verify the functionality of newly added IdPs and SPs.

**fed-metadata.xml**: Production metadata containing all approved entities. Entities validated in the test environment are promoted here, and all production services operate based on this file.

**fed-metadata-edugain.xml**: Approved entities with eduGAIN participation enabled, used for metadata exchange with the eduGAIN service. Consistent with the opt‑in / opt‑out models outlined below, this file only includes entities explicitly opted into eduGAIN; those opting out are excluded.

### About opt-in/opt-out

FedAdmin supports both opt-in and opt-out models for managing entities in the federation:

**Opt-In**: Each Service Provider (SP) and Identity Provider (IdP) must be explicitly configured to participate in eduGAIN. This gives federations more control over which entities are exposed to eduGAIN.

**Opt-Out**: All entities automatically participate in eduGAIN by default, with the option for individual entities to opt-out if needed. This provides a simpler, more automated workflow.

See [Guide for Joining eduGAIN as a Federation](https://wiki.geant.org/display/eduGAIN/Guide+for+Joining+eduGAIN+as+a+Federation) for detailed information about these models and recommendations for your federation.

FedAdmin provides a unique approach by allowing administrators to decide whether to include each IdP/SP in eduGAIN during entity creation, thereby supporting both opt-in and opt-out models.

## 2. Project Overview

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

### Technology Stack

- **Backend Framework**: Flask
- **ORM**: Flask-SQLAlchemy
- **Authentication**: Flask-Security-Too
- **Admin Interface**: Flask-Admin
- **Metadata Aggregation**: pyFF

## 3. Setup Development Environment
See [Setup Development Environment](docs/deployment/deployment_dev.md)

## 4. Production Deployment
See [Production Deployment](docs/deployment/deployment_prod.md)

## 5. User Guide
See [User Guide](docs/guides/user_guide.md)

## 6. Technical Details

### Storage
See [Storage](docs/reference/storage.md)

### SAML Metadata Processing
See [SAML Metadata Processing](docs/reference/metadata_processing.md)

### Scheduled Tasks
See [Scheduled Tasks](docs/deployment/scheduled_tasks.md)

## 7. Backlog and known issues

### Backlog
See [Backlog](docs/reference/backlog.md)

### Known issues
See [Known issues](docs/reference/issues.md)

## 8. Referenced Specifications

This project references the following open standards and specifications:

| Specification | Description |
|---------------|-------------|
| [SAML V2.0 Metadata](https://docs.oasis-open.org/security/saml/v2.0/saml-metadata-2.0-os.pdf) | Core SAML 2.0 metadata specification |
| [SAML V2.0 Metadata Extension for Entity Attributes](https://docs.oasis-open.org/security/saml/Post2.0/sstc-metadata-attr.pdf) | `mdattr:EntityAttributes` extension |
| [SAML V2.0 Metadata Extensions for Registration and Publication Information](https://docs.oasis-open.org/security/saml/Post2.0/saml-metadata-rpi/v1.0/saml-metadata-rpi-v1.0.pdf) | `mdrpi` extensions |
| [SAML V2.0 Metadata Extensions for Login and Discovery User Interface](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-ui/v1.0/sstc-saml-metadata-ui-v1.0.pdf) | `mdui`  extensions |
| [SAML 2.0 Metadata Extensions for Shibboleth](https://shibboleth.atlassian.net/wiki/spaces/SC/pages/1843888238/ShibMetaExt) | `shibmd:Scope` and `shibmd:KeyAuthority` (not used in this project) extensions |
| [REFEDS Security Contact Metadata Extension](http://refeds.org/metadata) | `remd:contactType` extension |
| [REFEDS Sirtfi Framework](https://refeds.org/sirtfi/) | Security Incident Response Trust Framework for Federated identity |
| [REFEDS Research & Scholarship](https://refeds.org/category/research-and-scholarship/) | Entity category for research and scholarship collaboration |
| [REFEDS Code of Conduct](https://refeds.org/category/code-of-conduct/) | Data protection and privacy guidelines for service providers |

## 9. Glossary
See [Glossary](docs/reference/glossary.md)

## 10. License

This project is licensed under the MIT License.
