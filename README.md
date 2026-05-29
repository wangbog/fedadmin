<!-- Badges -->
<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/Python-3.12+-yellow.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Flask-3.1.3-green.svg" alt="Flask">
</p>

# FedAdmin (NRENIdFedAdmin)

A web based management tool for NREN identity federation administrators to operate federations, managing Identity Providers (IdPs) and Service Providers (SPs), and exchanging metadata with eduGAIN metadata service.

## 1. About FedAdmin

### Project Background

We are the **CARSI** team, which manages CERNET (China Education and Research NETwork) Identity Federation.

The China Education and Research Network Federated Authentication and Resource Sharing Infrastructure (**CARSI**) provides federal authentication and global academic information resource sharing services for universities and research institutions that have established unified identity management systems on campus networks. CARSI joined eduGAIN in 2019 and over the years it covers over 1000 Chinese universities and institutes.

Based on this practical experience, we decided to share our knowledge and tools through this open-source project. (For more information about CARSI, please refer to https://www.carsi.edu.cn)

**Author's voice**: I am a core member of the CARSI team. I strive to make this project comprehensive enough to be directly deployed as a production environment by new NREN identity federation administrators with reduced deployment and management costs. However, it is still recommended to conduct thorough testing before formal use and read all documentation (especially [Backlog](docs/reference/backlog.md) and [Known Issues](docs/reference/issues.md)) to fully understand the current limitations.

### Who/When/Why Use FedAdmin

- **Who**: Federation administrators who are responsible for managing their NREN's identity federation.
- **When**: Your NREN has already joined or is in the process of joining eduGAIN, and you are now planning a technical tool to manage the federation's IdPs and SPs.
- **Why**: 
  - This management concept and workflow have been successfully used in CARSI's actual projects for many years
  - The system can meet common federation management scenarios and shield the complexity of SAML metadata
  - It provides a solution for operating federations and exchanging metadata with eduGAIN metadata service

See [eduGAIN: Join As Federation](https://technical.edugain.org/joining_checklist) for a practical checklist before joining eduGAIN.

### Primary Deliverables

Administrators of NREN identity federations use this project to manage their federation’s Identity Providers (IdPs) and Service Providers (SPs). The primary deliverables are federation metadata files stored under `./app/storage/public/federation/` (the final host‑side path may vary depending on deployment configuration):

FedAdmin assumes that a federation normally needs two operational environments:

- **Test environment**: A pre-production environment isolated from production. Member organizations can add IdP/SP entities by themselves, and newly added entities are immediately included in the beta federation metadata without waiting for federation administrator approval. This allows members to debug SAML metadata, login flows, attribute release, and SP integration before the entity is promoted to production.
- **Production environment**: The formal federation environment used by production IdPs, SPs. Only entities that have passed member-side testing and federation administrator approval are included here.

CARSI operates this two-environment workflow in practice. For the test environment, CARSI also provides a test IdP with test user accounts, a test SP that displays released user attributes after login, and a test DS (Discovery Service) for selecting institutions. This lets a member organization focus on the entity it is adding: when adding a SP, it can test against the federation-provided test IdP; when adding an IdP, it can test against the federation-provided test SP. We recommend that new federations provide similar test and production environments so that metadata promotion and troubleshooting are smoother.

The three federation metadata files map to these stages:

- **fed-metadata-beta.xml**: Beta metadata for entities in the test environment. It includes entities in `INIT` or `APPROVING` status, so newly added entities can be tested immediately before they are approved for production.
- **fed-metadata.xml**: Production metadata containing all approved entities. Entities validated in the test environment are promoted here after federation administrator approval, and all production services operate based on this file.
- **fed-metadata-edugain.xml**: Approved entities with eduGAIN participation enabled, used for metadata exchange with the eduGAIN service. Consistent with the opt‑in / opt‑out models outlined below, this file only includes entities explicitly opted into eduGAIN; those opting out are excluded.

### About opt-in/opt-out

FedAdmin supports both opt-in and opt-out models for managing entities in the federation:

- **Opt-In**: Each Service Provider (SP) and Identity Provider (IdP) must be explicitly configured to participate in eduGAIN. This gives federations more control over which entities are exposed to eduGAIN.
- **Opt-Out**: All entities automatically participate in eduGAIN by default, with the option for individual entities to opt-out if needed. This provides a simpler, more automated workflow.

See [Guide for Joining eduGAIN as a Federation](https://wiki.geant.org/display/eduGAIN/Guide+for+Joining+eduGAIN+as+a+Federation) for detailed information about these models and recommendations for your federation.

FedAdmin provides a unique approach by allowing administrators to decide whether to include each IdP/SP in eduGAIN during entity creation, thereby supporting both opt-in and opt-out models.

## 2. Project Overview

### System Organization

The system is organized into two main administrative modules with distinct roles and responsibilities:

#### Entity Status and Approval Workflow

IdP and SP entities use three statuses:

- **`INIT`**: The entity is in the test/debugging stage. Member organizations can create, edit, delete, and test the entity. The entity is included in `fed-metadata-beta.xml`, but not in production metadata.
- **`APPROVING`**: The entity has been submitted by the member organization for federation administrator review. It still remains in `fed-metadata-beta.xml` and is not yet available in production.
- **`READY`**: The entity has been approved and is online in production. It is included in `fed-metadata.xml`; if eduGAIN participation is enabled, it is also included in `fed-metadata-edugain.xml`.

The approval workflow exists to separate member-side testing from production publication. A member organization first creates and tests an entity in `INIT`. When testing is complete, the member submits it for approval, which changes the status to `APPROVING`. A federation administrator can then approve it, changing the status to `READY` and regenerating production federation metadata. Conceptually, approval promotes the entity metadata from the test federation metadata into the production federation metadata. The federation administrator can also reject the application, returning it to `INIT` for further debugging.

#### Federation Administration (`/federation`)
- **User Roles**: `federation` (federation administrator)
- **Permissions**: Full access to all organizations and entities
- **Core Functions**:
  - Entity approval workflow (approve/reject pending applications)
  - Federation metadata aggregation and digital signing
  - Federation configuration and certificate management
  - Member organization management

#### Member Administration (`/member`)
- **User Roles**: Member administrator roles are scoped to a member organization and determine which entity types the organization can maintain:
  - `full_member`: The member organization can maintain both IdP and SP entities
  - `sp_member`: The member organization can maintain SP entities only
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

## 8. Contributing and Security

See [Contributing](.github/CONTRIBUTING.md) for development and pull request guidance.

Please report security issues privately. See [Security Policy](.github/SECURITY.md).

## 9. Referenced Specifications

This project references the following open standards and specifications:

| Specification | Description |
|---------------|-------------|
| [SAML V2.0 Metadata](https://docs.oasis-open.org/security/saml/v2.0/saml-metadata-2.0-os.pdf) | Core SAML V2.0 metadata specification (`md:`) |
| [SAML V2.0 Core Assertion & Protocol](https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf) | SAML assertions, attributes and protocol messages (`saml:`) |
| [SAML V2.0 Metadata Extension for Entity Attributes](https://docs.oasis-open.org/security/saml/Post2.0/sstc-metadata-attr.pdf) | `mdattr:EntityAttributes` extension |
| [SAML V2.0 Metadata Extensions for Registration and Publication Information](https://docs.oasis-open.org/security/saml/Post2.0/saml-metadata-rpi/v1.0/saml-metadata-rpi-v1.0.pdf) | `mdrpi:` registration & publication metadata |
| [SAML V2.0 Metadata Extensions for Login and Discovery User Interface](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-ui/v1.0/sstc-saml-metadata-ui-v1.0.pdf) | `mdui:` UI, logo and discovery hints |
| [SAML V2.0 Metadata Extension for Algorithm Support](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-algsupport.pdf) | `alg:` signature/digest/encryption algorithms |
| [Shibboleth Metadata Extensions](https://shibboleth.atlassian.net/wiki/spaces/SC/pages/1843888238/ShibMetaExt) | `shibmd:Scope` and `shibmd:KeyAuthority` (unused) |
| [XML Digital Signature (XMLDSig)](http://www.w3.org/TR/xmldsig-core/) | `ds:` signature, digest and key information |
| [REFEDS Security Contact Metadata Extension](http://refeds.org/metadata) | `remd:contactType` for security contacts |
| [REFEDS Sirtfi Framework](https://refeds.org/sirtfi/) | Security Incident Response Trust Framework |
| [REFEDS Research & Scholarship Category](https://refeds.org/category/research-and-scholarship/) | Research & Scholarship entity category for academic federations |
| [REFEDS Code of Conduct](https://refeds.org/category/code-of-conduct/) | Data protection and privacy code of conduct |

## 10. Glossary
See [Glossary](docs/reference/glossary.md)

## 11. License

This project is licensed under the [MIT License](LICENSE).
