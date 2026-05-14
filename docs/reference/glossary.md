# FedAdmin Glossary

This glossary defines key terms related to federated identity management and the FedAdmin system.

## General Terms

- **Federation** - A group of organizations that agree to trust each other's authentication mechanisms for identity assertion.
- **Identity Provider (IdP)** - A system entity that creates, maintains, and manages identity information for principals (users) and provides identity assertions to other trusted systems.
- **Service Provider (SP)** - A system entity that consumes identity information from Identity Providers to make access control decisions.
- **Entity** - A representation of an IdP or SP within the federation, defined by SAML metadata.
- **Metadata** - XML documents that describe the technical and administrative information about entities in a federation.

## FedAdmin Specific Terms

- **Federation Administrator** - User role with full access to all organizations and entities, responsible for federation-wide operations.
- **Member Administrator** - User role with access limited to their own organization's data, responsible for managing entities within their organization.
- **Organization** - An entity that belongs to the federation and can contain users and IdP/SP entities.
- **Organization Status** - The current state of an organization (e.g., READY, PENDING).
- **Entity Status** - The current state of an IdP/SP entity (e.g., INIT, APPROVING, READY).
- **eduGAIN** - The European educational identity and access management federation, allowing exchange of identity information between national education and research federations.

## SAML Terms

- **SAML (Security Assertion Markup Language)** - XML-based open standard for exchanging authentication and authorization data between parties.
- **SAML Metadata** - XML format that describes the capabilities and requirements of SAML entities.
- **EntityDescriptor** - SAML metadata element that describes a single entity (either an IdP or SP).
- **EntitiesDescriptor** - SAML metadata element that contains multiple EntityDescriptor elements.
- **EntityID** - Unique identifier for an entity within a federation.
- **SSO (Single Sign-On)** - Authentication mechanism that allows users to access multiple applications with a single login.
- **IDPSSODescriptor** - SAML metadata element that describes an Identity Provider's SSO capabilities.
- **SPSSODescriptor** - SAML metadata element that describes a Service Provider's SSO capabilities.

## Metadata Processing Terms

- **Metadata Validation** - Process of verifying that uploaded metadata conforms to required schemas and business rules.
- **Metadata Transformation** - Process of adding federation-specific extensions to uploaded metadata.
- **Metadata Aggregation** - Process of combining multiple entity metadata files into federation-wide metadata files.
- **Metadata Signing** - Process of adding digital signatures to aggregated metadata files to ensure authenticity and integrity.
- **XSLT Transformation** - XML-based language used for transforming metadata files into federation format.
- **pyFF** - Python-based toolkit for processing SAML metadata, used for aggregation and transformation.

## Workflow Terms

- **Entity Registration** - Process of creating and submitting new IdP/SP entities for approval.
- **Entity Approval** - Process where Federation Administrators review and approve submitted entities.
- **Entity Lifecycle** - States through which an entity passes from creation to deactivation (INIT → APPROVING → READY → INACTIVE).
- **Withdrawal** - Process by which an organization can remove an entity from the federation.

## Technical Terms

- **APScheduler** - Python library used for scheduled tasks in FedAdmin.
- **Flask-Security-Too** - Extension that provides security features to Flask applications.
- **Flask-Admin** - Extension that provides admin interface for Flask applications.
- **SQLAlchemy** - Python SQL toolkit and Object-Relational Mapping (ORM) library.
- **WSGI** - Web Server Gateway Interface, standard for Python web applications.
- **Gunicorn** - WSGI HTTP server for Python applications, used in production deployments.
- **Docker** - Platform for developing, shipping, and running applications in containers.