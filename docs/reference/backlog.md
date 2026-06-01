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

Users created by Federation Administrators or Member Administrators set their password through a password setup/reset link. FedAdmin attempts to email the link to the user's email address, records the delivery status, and shows the link once to the administrator after user creation. Setup/reset links must be treated as credential-equivalent one-time links and shared only through trusted channels.

The initial federation administrator created by `flask init-db` uses a randomly generated password that is printed once on the console.

Password setup, reset, and change flows use Flask-Security password validation with a minimum length of 8 characters and zxcvbn strength scoring enabled.

**Remaining Security Recommendations:**
1. Review whether the minimum password length should be raised for production deployments
2. Evaluate breached password checks, including operational impact of the external lookup dependency
3. Implement mandatory email verification to validate user identities
4. Add account lockout mechanisms after failed login attempts to prevent brute force attacks
5. Implement Multi-Factor Authentication (MFA) to add an additional layer of security beyond just passwords
6. Consider adding administrator actions to resend password setup/reset links for existing users

## 3. Flask-Security Email Customization

FedAdmin currently uses Flask-Security's built-in email templates and subject configuration. Future development should customize these emails as a complete set so account setup, password reset, password change notices, and related security emails have consistent FedAdmin wording and branding.

In this project, custom email templates should be placed under:

```text
app/templates/security/email/
```

For each Flask-Security email, provide both formats when customizing:

- `*.txt`: plain-text email body for clients that do not render HTML
- `*.html`: HTML email body for clients that support formatted email

For example, password reset/setup emails can be customized with:

```text
app/templates/security/email/reset_instructions.txt
app/templates/security/email/reset_instructions.html
```

Use the official Flask-Security guide for the complete template list, subject configuration keys, available context variables, and signals:

- https://flask-security.readthedocs.io/en/latest/customizing.html#emails

## 4. Synchronous Metadata Transformation and Regeneration

FedAdmin performs metadata transformation and federation metadata regeneration synchronously as part of the request flow.

Entity create/edit operations must produce a transformed metadata file before beta metadata is regenerated. If transformation fails, the user sees an error and metadata regeneration is skipped.

Before an entity can be submitted for approval, FedAdmin checks that its transformed metadata file exists and is at least as new as the uploaded source metadata. This prevents an entity from entering approval with missing or stale transformed metadata.

When member organization or federation information is modified, the system synchronously re-transforms the affected entities except eduGAIN `ALREADY_IN` records, and regenerates federation metadata only if all transformations succeed. If any entity fails, the UI reports the failed entities and metadata regeneration is skipped.

Approval and withdrawal require successful production metadata regeneration before the status change is committed. If production metadata cannot be regenerated, the entity remains in its previous status. Beta-only create, edit, and delete operations report regeneration failures to the user and require beta metadata to be regenerated after the issue is fixed.

**Potential Improvement:**
Synchronous transformation and regeneration gives immediate feedback and avoids hidden failures, but it may have performance implications for federations with many entities. Consider implementing asynchronous processing with equivalent failure reporting and publication safeguards.

This would improve system responsiveness, especially during bulk updates or when working with large federations.

Another future improvement is to add an explicit metadata publication health state, such as `metadata_dirty`, `metadata_failed`, and the last successful generation timestamp. Some beta-only create, edit, and delete flows intentionally keep the business data change after a metadata regeneration failure and report the problem to the user. A visible state would make that degraded condition easier to monitor, retry, and operationally distinguish from successfully published metadata.

**Implementation Considerations:**
An asynchronous implementation should account for these constraints:

1. **APScheduler pkg_resources Deprecation Warning**
   
   This project uses `pyFF==2.1.5` which depends on **APScheduler 3.6.3**, an older version that imports the deprecated `pkg_resources` API. This causes warnings during initialization:

   ```
   /usr/local/lib/python3.12/site-packages/apscheduler/__init__.py:1: UserWarning: pkg_resources is deprecated as an API... The pkg_resources package is slated for removal as early as 2025-11-30.
   ```

   APScheduler will fail after `pkg_resources` is removed (2025-11-30). Upgrading APScheduler may affect pyFF compatibility.

2. **Production Environment Multi-process Constraints**
   
   In-process schedulers are not suitable for Gunicorn-style multi-process production deployments. Queue-based alternatives such as Redis-backed workers, database-backed schedulers, or Celery introduce additional infrastructure dependencies beyond the current lightweight architecture.

## 5. Placeholder Federation Metadata Requirement

When the federation is empty (no entities), the system automatically generates a placeholder metadata XML containing a placeholder EntityDescriptor with an SPSSODescriptor. This placeholder is required by the SAML v2.0 XSD schema and pyFF signing process.

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

The placeholder metadata automatically generated when the federation is empty follows this structure. In addition to the SPSSODescriptor required to satisfy schema and signing requirements, it includes `mdrpi:RegistrationInfo`, `mdui:UIInfo`, `md:Organization`, and a technical `md:ContactPerson` so profile-oriented validators such as the eduGAIN validator do not treat the placeholder as a malformed entity.

The organization name and URL are derived from the default `FEDERATION_ADMIN` organization created by `init-db`. The technical contact email is derived from an active user in that organization. The logo URL is a placeholder URL derived from the federation admin organization URL.

```xml
<md:EntityDescriptor entityID="{registration_authority}/placeholder">
    <md:Extensions>
        <mdrpi:RegistrationInfo
            registrationAuthority="{registration_authority}"
            registrationInstant="{generation_time}">
            <mdrpi:RegistrationPolicy xml:lang="en">
                {registration_policy_url}
            </mdrpi:RegistrationPolicy>
        </mdrpi:RegistrationInfo>
    </md:Extensions>
    <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:Extensions>
            <mdui:UIInfo>
                <mdui:DisplayName xml:lang="en">
                    {federation_name} Placeholder SP
                </mdui:DisplayName>
                <mdui:Description xml:lang="en">
                    Placeholder SP metadata used only when the federation has no entities.
                </mdui:Description>
                <mdui:Logo width="80" height="80">
                    {federation_admin_organization_url}/placeholder/logo.png
                </mdui:Logo>
            </mdui:UIInfo>
        </md:Extensions>
        <md:AssertionConsumerService 
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" 
            Location="{registration_authority}/placeholder/acs" 
            index="0"/>
    </md:SPSSODescriptor>
    <md:Organization>
        <md:OrganizationName xml:lang="en">{federation_name}</md:OrganizationName>
        <md:OrganizationDisplayName xml:lang="en">{federation_name}</md:OrganizationDisplayName>
        <md:OrganizationURL xml:lang="en">{federation_admin_organization_url}</md:OrganizationURL>
    </md:Organization>
    <md:ContactPerson contactType="technical">
        <md:GivenName>Federation Technical Contact</md:GivenName>
        <md:EmailAddress>mailto:{technical_contact}</md:EmailAddress>
    </md:ContactPerson>
</md:EntityDescriptor>
```

### Implementation Location

The placeholder is generated in `./app/services/metadata.py` in the `_create_empty_metadata_xml()` method.

### Federation Metadata Publication Considerations

Consider publication timing carefully to avoid publishing metadata that only contains placeholder entities. Federation metadata should be published only when actual entities are registered and available.

## 6. Multilingual Metadata Support

FedAdmin currently generates localized SAML metadata elements only in English (`xml:lang="en"`). This applies to organization information such as `OrganizationName`, `OrganizationDisplayName`, and `OrganizationURL`, as well as MDUI elements such as `DisplayName`, `Description`, `InformationURL`, and `PrivacyStatementURL`.

This is acceptable for basic SAML metadata generation and may pass eduGAIN validator checks when no local language tag is selected. However, the eduGAIN SAML Profile recommends that entities provide English variants and, where appropriate, local-language variants for user-facing metadata. If a federation administrator explicitly selects a local language tag in the eduGAIN validator, the validator may warn that these elements do not have the native-language version.

The current eduGAIN validator language selector appears to focus mainly on European languages, which may reflect the historical and operational context of eduGAIN. FedAdmin is intended as an open-source tool for NREN identity federations more broadly, including federations in countries or regions that have not yet joined eduGAIN. Therefore, future multilingual support should not be limited to the current validator language list.

**Future Enhancement:**
Future development should consider adding configurable multilingual metadata support, including:

1. Federation-level configuration for default language and local language tags
2. Localized organization fields for member organizations
3. Localized IdP/SP display names and descriptions
4. Localized SP information and privacy statement URLs
5. Metadata transformation logic that emits multiple `xml:lang` variants instead of replacing all localized elements with English-only values
6. Validation or warning checks for missing English or configured local-language variants

## 7. Production Docker Image Slimming

The current production Docker image installs build-time packages such as `build-essential` and `python3-dev` directly in the final runtime image. These packages are mainly needed while `pip install -r requirements.txt` builds Python packages with native extensions. The running application normally only needs runtime libraries.

**Future Enhancement:**
Consider converting `Dockerfile.prod` to a multi-stage build. The builder stage would install compilers, development headers, and Python wheels. The final stage would copy only installed Python packages, application code, and runtime system libraries.

This would reduce image size and remove unnecessary compiler tooling from the production container. The change should be tested by building the production image, importing key dependencies such as `xmlsec`, `magic`, and `lxml`, running `pyff --version`, and starting Gunicorn with the production entry point.

## 8. Production Database Backend

The current production deployment uses SQLite for simplicity. This is acceptable for small, low-concurrency deployments, but the Gunicorn production configuration uses multiple workers and threads, and scheduled jobs can run while administrators are using the web UI. These concurrent write paths may lead to SQLite lock contention under real production load.

**Future Enhancement:**
Evaluate a production database backend such as PostgreSQL or MySQL, or provide an explicit single-writer SQLite production profile for lightweight deployments. If a server database is added, document backup, migration, connection pooling, and operational requirements alongside the existing Docker deployment guide.
