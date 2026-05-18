<!-- Badges -->
<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/Python-3.12+-yellow.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Flask-3.1.3-green.svg" alt="Flask">
</p>

# FedAdmin

A web based management tool for NREN identity federation administrators to operate federations in a scalable manner, managing Identity Providers (IdPs) and Service Providers (SPs), and exchanging metadata with eduGAIN metadata service in an automated manner.

## 1. About FedAdmin

### Project Background

We are the CARSI team, which manages China's NREN Identity Federation. 

**About CARSI**: The China Education and Research Computer Network Federated Authentication and Resource Sharing Infrastructure (CARSI) provides federal authentication and global academic information resource sharing services for universities and research institutions that have established unified identity authentication on campus networks. No VPN is required, and is not restricted by the authorization of the campus IP address. You can directly access authorized resources using a campus network account anywhere with the internet.

CARSI joined eduGAIN and over the years we have accumulated extensive experience in managing federations. Based on this practical experience, we decided to share our knowledge and tools through this open-source project. (For more information about CARSI, please refer to https://www.carsi.edu.cn/index_en.html)

### Who/When/Why Use FedAdmin

**Who**: Federation administrators who are responsible for managing their NREN's identity federation.

**When**: Your NREN has already joined or is in the process of joining eduGAIN, and you are now planning a technical tool to manage the federation's IdPs/SPs.

**Why**: 
- This management concept and workflow have been successfully used in CARSI's actual projects for many years
- The system can meet common federation management scenarios and shield the complexity of SAML metadata
- It provides a scalable solution for operating federations and exchanging metadata with eduGAIN metadata service in an automated manner

See [eduGAIN: Join As Federation](https://technical.edugain.org/joining_checklist) for a practical checklist before joining eduGAIN.

### About opt-in/opt-out

FedAdmin supports both opt-in and opt-out models for managing entities in the federation:

**Opt-In**: Each Service Provider (SP) and Identity Provider (IdP) must be explicitly configured to participate in eduGAIN. This gives federations more control over which entities are exposed to eduGAIN.

**Opt-Out**: All entities automatically participate in eduGAIN by default, with the option for individual entities to opt-out if needed. This provides a simpler, more automated workflow.

See [Guide for Joining eduGAIN as a Federation](https://wiki.geant.org/spaces/eduGAIN/pages/121348068/Guide+for+Joining+eduGAIN+as+a+Federation) for detailed information about these models and recommendations for your federation.

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

- **Backend Framework**: Flask 3.1.3
- **ORM**: Flask-SQLAlchemy 3.1.1
- **Authentication**: Flask-Security-Too 5.7.1
- **Admin Interface**: Flask-Admin[images] 2.0.2
- **Metadata Aggregation**: pyFF 2.1.5

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

## 7. Backlog and known issues

### Backlog
See [Backlog](docs/reference/backlog.md)

### Known issues
See [Known issues](docs/reference/issues.md)

## 8. Referenced Specifications

| Specification | Description |
|---------------|-------------|
| [SAML V2.0 Metadata](https://docs.oasis-open.org/security/saml/v2.0/saml-metadata-2.0-os.pdf) | Core SAML 2.0 metadata specification |
| [SAML V2.0 Metadata Interoperability Profile](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-iop/v1.0/os/sstc-saml-metadata-iop-v1.0-os.html) | Interoperability guidelines for SAML metadata |
| [REFEDS Sirtfi Framework](https://refeds.org/sirtfi/) | Security Incident Response Trust Framework for Federated identity |
| [REFEDS Research & Scholarship](https://refeds.org/category/research-and-scholarship/) | Entity category for research and scholarship collaboration |
| [REFEDS Code of Conduct](https://refeds.org/category/code-of-conduct/) | Data protection and privacy guidelines for service providers |
| [Shibboleth Metadata Profile](https://wiki.shibboleth.net/confluence/display/SHIB/Metadata+Profiles) | Shibboleth-specific metadata extensions |
| [XML-Signature Syntax and Processing](https://www.w3.org/TR/xmldsig-core1/) | W3C standard for XML digital signatures |
| [mdrpi:RegistrationInfo](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-rpi/v1.0/os/sstc-saml-metadata-rpi-v1.0-os.html) | SAML Metadata Registration Information |
| [mdui:UIInfo](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-ui/v1.0/os/sstc-saml-metadata-ui-v1.0-os.html) | SAML Metadata User Interface Extension |

## 9. Glossary
See [Glossary](docs/reference/glossary.md)

## 10. License

This project is licensed under the MIT License.
