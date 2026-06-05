<!-- Badges -->
<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/Python-3.12+-yellow.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Flask-3.1.3-green.svg" alt="Flask">
</p>

# FedAdmin (NRENIdFedAdmin)

A web-based management tool for NREN identity federation administrators to operate federations, manage Identity Providers (IdPs) and Service Providers (SPs), and exchange metadata with the eduGAIN metadata service.

## 1. About FedAdmin

### Project Background

FedAdmin is based on practical experience from the [CARSI](https://www.carsi.edu.cn/index_en.html) team operating the CERNET (China Education and Research NETwork) Identity Federation, which joined eduGAIN in 2019.

We decided to share this knowledge and tooling through an open-source project. The goal is to provide a practical system that new NREN identity federation administrators can evaluate, adapt, and deploy with reduced implementation effort. However, it is still recommended to conduct thorough testing before formal use and read all documentation, especially [Backlog](docs/reference/backlog.md) and [Known Issues](docs/reference/issues.md), to fully understand the current limitations.

### Who/When/Why Use FedAdmin

- **Who**: Federation administrators who are responsible for operating their NREN's identity federation.
- **When**: Your NREN has already joined or is in the process of joining eduGAIN, and you are now planning a technical tool to manage the federation's IdPs and SPs.
- **Why**: 
  - The project is based on practical experience operating identity federation services
  - The system can meet common federation management scenarios and shield the complexity of SAML metadata
  - It provides a solution for operating federations and exchanging metadata with the eduGAIN metadata service

See [eduGAIN: Join As Federation](https://technical.edugain.org/joining_checklist) for a practical checklist before joining eduGAIN.

## 2. Core Concepts

FedAdmin is organized around six core concepts used by identity federations: two memberships, two types of Admin, two operational phases, three metadata files, eduGAIN participation policies, and three entity statuses.

### Two Memberships

FedAdmin supports two member organization types:

- **Full member**: The organization can manage both Identity Provider (IdP) and Service Provider (SP) entities.
- **SP member**: The organization can manage SP entities only.

These membership types determine what a member organization can maintain after it receives access to the system.

### Two types of Admin

FedAdmin provides two administration interfaces.

- **Federation Admin** (`/federation`) is used by Federation Administrators to manage organizations, administrator accounts, federation configuration, entity approval, metadata aggregation, signing certificates, and metadata publication.

- **Member Admin** (`/member`) is used by member organization administrators. After a Federation Administrator creates the member organization, assigns its membership type, and creates one or more administrator accounts, member organization administrators can log in to manage their own organization profile and administrators, and add or manage IdP/SP entities allowed by their membership type. A Full Member Administrator can add and manage both IdPs and SPs; an SP Member Administrator can add and manage SPs only.

See [Administrator Guide](docs/guides/user_guide.md) for detailed administrator workflows.

### Member Onboarding Flow

The following table summarizes the current high-level flow for bringing a member organization into the federation.

| Stage | Member Organization Administrator | Federation Administrator |
|-------|-----------------------------------|--------------------------|
| Membership application | Provides organization and contact information through the federation's current offline or external process | Reviews the application, then creates the organization and administrator accounts |
| Technical testing | Logs in to the FedAdmin system with a Member Admin account, completes organization information, adds or edits IdP/SP entities, and tests them using beta federation metadata | Supports troubleshooting and reviews submitted entities when they are ready for production |
| Production operation | Submits tested entities for approval, maintains organization and entity information, and withdraws production entities when needed | Approves or rejects submitted entities and publishes them to the federation production metadata |

The technical testing and production operation stages correspond to the entity status and metadata relationships summarized in the [Concept Map](#concept-map) below.

### Two Operational Phases

FedAdmin assumes that a federation normally has two operational phases:

- **Beta phase**: The IdP/SP deployment and testing phase. Member organizations can create, edit, delete, and test entities using the beta federation metadata.
- **Production phase**: The formal federation operation phase. Only `READY` status entities are included in production federation metadata.

For smoother member-side testing, a federation should prepare a small set of test services for the Beta phase. Except for the beta federation metadata feed, these services are deployed according to other eduGAIN guidance and are not included in FedAdmin.

| Test Service | Type | Purpose |
|--------------|------|---------|
| Test IdP | Identity Provider | Lets newly registered SPs test login, metadata configuration, signing/encryption settings, and requested attributes |
| Test SP | Service Provider | Lets newly registered IdPs test authentication, attribute release, and user-facing login behavior |
| Test Discovery Service | Discovery Service | Lets IdPs and SPs test institution discovery, display names, logos, and redirect behavior before production |
| Beta federation metadata URL | Metadata feed | Publishes `INIT` and `APPROVING` entities for technical debugging before production approval |

### Three Metadata Files

The primary deliverables of FedAdmin are federation metadata files stored under `./app/storage/public/federation/` (the final host-side path may vary depending on deployment configuration). FedAdmin automatically aggregates member metadata and signs the federation metadata files.

- **`fed-metadata-beta.xml`**: Metadata for entities in the Beta phase. It includes entities in `INIT` or `APPROVING` status.
- **`fed-metadata.xml`**: Metadata for entities in the Production phase. It includes entities in `READY` status.
- **`fed-metadata-edugain.xml`**: Outbound eduGAIN exchange metadata containing this federation's `READY` status IdP/SP entities whose eduGAIN participation option is enabled.

### eduGAIN Participation Policies

FedAdmin supports both opt-in and opt-out models for managing which entities are included in the federation's eduGAIN metadata file:

- **Opt-in**: Each IdP/SP must be explicitly configured to participate in eduGAIN. This gives federations more control over which entities are exposed to eduGAIN.
- **Opt-out**: IdP/SP entities participate in eduGAIN by default, with the option to exclude individual entities when needed. This provides a simpler, more automated workflow.

In practice, each IdP/SP has an eduGAIN participation option during entity creation. `fed-metadata-edugain.xml` includes only `READY` status entities whose setting makes them eligible for eduGAIN exchange.

See [Guide for Joining eduGAIN as a Federation](https://wiki.geant.org/display/eduGAIN/Guide+for+Joining+eduGAIN+as+a+Federation) for detailed information about eduGAIN participation models and recommendations for your federation.

### Three Entity Statuses

IdP and SP entities use the same three-status lifecycle:

- **`INIT`**: The entity is in the Beta phase. Member organizations can create, edit, delete, and test it. It is included in `fed-metadata-beta.xml`, but not in production metadata.
- **`APPROVING`**: The entity has been submitted by the member organization for federation administrator review and remains in the Beta phase. It remains in `fed-metadata-beta.xml`, but is not yet included in production metadata.
- **`READY`**: The entity has been approved by a Federation Administrator and is in the Production phase. It is included in `fed-metadata.xml`; if it is eligible for eduGAIN participation, it is also included in `fed-metadata-edugain.xml`.

The approval workflow separates member-side testing from production publication. A member organization first creates and tests an entity in `INIT`. When testing is complete, the member submits it for approval, changing it to `APPROVING`. A federation administrator can approve it, changing it to `READY`, or reject it back to `INIT` for further work.

### Concept Map

The following table summarizes how entity statuses map to operational phases and metadata files, with the relevant admin roles and membership context.

| Entity Status | Operational Phase | Metadata File | Admin Role | Membership / Role Context | Meaning |
|---------------|-------------------|-----------------|------------|---------------------------|---------|
| `INIT` | Beta phase | `fed-metadata-beta.xml` | Member Admin | Full Member Administrator: IdP/SP; SP Member Administrator: SP only | Entity is being created, edited, and tested |
| `APPROVING` | Beta phase | `fed-metadata-beta.xml` | Member Admin and Federation Admin | Member organization administrators submit; Federation Administrators review | Entity is under federation review while still testable |
| `READY` | Production phase | `fed-metadata.xml` | Federation Admin | Federation Administrators approve | Entity is approved for formal federation operation |
| `READY` with eduGAIN participation enabled | Production phase / eduGAIN exchange | `fed-metadata-edugain.xml` | Federation Admin | Federation Administrators approve; eduGAIN option was set during entity creation | Entity is approved and eligible for eduGAIN metadata exchange |

## 3. Technology Stack

- **Backend Framework**: Flask
- **ORM**: Flask-SQLAlchemy
- **Authentication**: Flask-Security-Too
- **Admin Interface**: Flask-Admin
- **Metadata Aggregation**: pyFF

## 4. Setup Development Environment

Before deploying FedAdmin for your NREN identity federation, you may want to customize it for your federation's operational context. For example, you may need to adapt pages, adjust terminology, or simplify and extend management workflows. The following guide explains how to set up a development environment for that work.

See [Setup Development Environment](docs/deployment/deployment_dev.md)

## 5. Production Deployment

After customization and validation, use the production deployment guide to run FedAdmin with persistent storage, production configuration, metadata signing certificates, and a reverse proxy suitable for federation operations.

See [Production Deployment](docs/deployment/deployment_prod.md)

## 6. Administrator Guide

FedAdmin users are federation administrators and member organization administrators, not end users such as students, faculty, or researchers who authenticate through the federation.

See [Administrator Guide](docs/guides/user_guide.md)

## 7. Technical Details

### Storage
See [Storage](docs/reference/storage.md)

### SAML Metadata Processing
See [SAML Metadata Processing](docs/reference/metadata_processing.md)

### Scheduled Tasks
See [Scheduled Tasks](docs/deployment/scheduled_tasks.md)

## 8. Backlog and known issues

### Backlog
See [Backlog](docs/reference/backlog.md)

### Known issues
See [Known issues](docs/reference/issues.md)

## 9. Contributing and Security

See [Contributing](.github/CONTRIBUTING.md) for development and pull request guidance.

Please report security issues privately. See [Security Policy](.github/SECURITY.md).

## 10. Referenced Specifications

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

## 11. Glossary
See [Glossary](docs/reference/glossary.md)

## 12. License

This project is licensed under the [MIT License](LICENSE).
