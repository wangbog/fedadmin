# Backlog

This document describes future improvements and features planned for the FedAdmin system.

## 1. Organization and User Registration Process

The current business flow requires Federation Administrators to manually register Organizations and Users. Organizations must be created first by the Federation Administrator, followed by Users who are then assigned to these Organizations. This process is not designed for self-service registration by users.

**Future Enhancement:**
Future development should consider allowing member organizations to self-register online by submitting their organization information and creating default users. The Federation Administrator's role would be limited to reviewing and approving these registration requests, reducing the administrative burden and enabling faster onboarding of new members.

**Organization Status Field:**
- The Organization's `organization_status` field is currently a reserved field with no active functionality.
- It is recommended to set this field to `READY` for all organizations at this stage.
- Future development may implement registration/approval logic based on this status field, potentially supporting a multi-stage approval workflow (e.g., PENDING → APPROVED → READY).
- This would allow for more granular control over organization lifecycle management, including pending approvals, active status, and potentially inactive or suspended states.

## 2. Account Security Requirements

Users created by Federation Administrators or Member Administrators are assigned their username as the default password. Upon first login, users are required to change their password. Currently, the system does not enforce email verification or password complexity requirements.

**Security Concerns and Recommendations:**
This practice is highly insecure and poses significant security risks. Using usernames as default passwords creates predictable credentials that are easily guessed by attackers. Recommendations for improvement include:
1. Implement secure password generation during user creation (e.g., randomly generated complex passwords)
2. Enforce strong password complexity requirements (minimum length, mix of character types)
3. Implement mandatory email verification to validate user identities
4. Consider using secure password reset flows instead of forcing password changes on first login
5. Add account lockout mechanisms after failed login attempts to prevent brute force attacks
6. Implement Multi-Factor Authentication (MFA) to add an additional layer of security beyond just passwords

## 3. Synchronous Metadata Transformation and Regeneration

When entities are created, updated, or deleted through the admin interface, the system synchronously transforms and regenerates the federation metadata automatically after each operation. 

When member organization or federation information is modified, the system synchronously transforms all entities belonging to that member organization or federation and regenerates the federation metadata automatically. 

**Potential Improvement:**
While synchronous transformation and regeneration ensures that metadata is always up-to-date, it may have performance implications for federations with many entities. Consider implementing asynchronous processing.

This would improve system responsiveness, especially during bulk updates or when working with large federations.

**Technical Background:**
We initially implemented APScheduler (with MemoryJobStore) for async processing but reverted to synchronous execution due to these challenges:

1. **APScheduler pkg_resources Deprecation Warning**
   
   This project uses `pyFF==2.1.5` which depends on **APScheduler 3.6.3**, an older version that imports the deprecated `pkg_resources` API. This causes warnings during initialization:

   ```
   /usr/local/lib/python3.12/site-packages/apscheduler/__init__.py:1: UserWarning: pkg_resources is deprecated as an API... The pkg_resources package is slated for removal as early as 2025-11-30.
   ```

   APScheduler will fail after `pkg_resources` is removed (2025-11-30). Upgrading APScheduler would break pyFF's functionality.

2. **Production Environment Multi-process Constraints**
   
   APScheduler works in single-process development but fails in Gunicorn's multi-production setup. Alternative solutions (Redis, database-backed schedulers, Celery) all introduce additional infrastructure dependencies beyond our lightweight architecture.

## 4. Placeholder Federation Metadata Requirement

When the federation is empty (no entities), the system automatically generates a placeholder metadata XML containing a minimal EntityDescriptor with an SPSSODescriptor. This placeholder is required by the SAML v2.0 XSD schema and pyFF signing process.

### XSD Schema Requirement

According to [SAML V2.0 Metadata Schema](https://docs.oasis-open.org/security/saml/v2.0/saml-schema-metadata-2.0.xsd), the `EntitiesDescriptor` element requires at least one child element:

```xml
<element name="EntitiesDescriptor" type="md:EntitiesDescriptorType"/>
<complexType name="EntitiesDescriptorType">
   <sequence>
      <element ref="ds:Signature" minOccurs="0"/>
      <element ref="md:Extensions" minOccurs="0"/>
      <choice minOccurs="1" maxOccurs="unbounded">
         <element ref="md:EntityDescriptor"/>
         <element ref="md:EntitiesDescriptor"/>
      </choice>
   </sequence>
   <attribute name="validUntil" type="dateTime" use="optional"/>
   <attribute name="cacheDuration" type="duration" use="optional"/>
   <attribute name="ID" type="ID" use="optional"/>
   <attribute name="Name" type="string" use="optional"/>
</complexType>
```

The `minOccurs="1"` on the `<choice>` element means that at least one EntityDescriptor or EntitiesDescriptor must be present. This is enforced during XSD validation by pyFF when signing the federation metadata.

### Placeholder Structure

The placeholder metadata automatically generated when the federation is empty follows this structure:

```xml
<md:EntityDescriptor entityID="https://<registration_authority>/placeholder">
    <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:AssertionConsumerService 
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" 
            Location="https://<registration_authority>/placeholder/acs" 
            index="0"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>
```

### Implementation Location

The placeholder is generated in `./app/services/metadata.py` in the `_create_empty_metadata_xml()` method.

### Federation Metadata Publication Considerations

Consider publication timing carefully to avoid publishing metadata that only contains placeholder entities. Federation metadata should be published only when actual entities are registered and available.
