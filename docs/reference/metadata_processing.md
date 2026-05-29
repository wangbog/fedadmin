# SAML Metadata Processing

The system implements comprehensive SAML metadata lifecycle management, including validation, transformation, and aggregation. All operations comply with SAML 2.0 specifications and REFEDS interoperability profiles.

## Metadata Validation

When an IdP or SP metadata file is uploaded, the system performs the following validation steps:

1. **File Validation**
   - Check for empty files
   - Validate MIME type (XML for metadata files)

2. **XML Structure Validation**
   - Parse XML and verify well-formedness
   - Ensure exactly one `EntityDescriptor` element (reject `EntitiesDescriptor`)
   - Validate root element is `EntityDescriptor`

3. **XSD Schema Validation**
   - Validate against [SAML V2.0 Metadata Schema](https://docs.oasis-open.org/security/saml/v2.0/saml-schema-metadata-2.0.xsd)
   - Validate against [Shibboleth Metadata Schema](https://shibboleth.atlassian.net/wiki/spaces/SC/pages/1843888238/ShibMetaExt) (if applicable)
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

## Metadata Transformation

After validation, the system transforms the uploaded metadata by adding federation-specific extensions:

1. **Registration Information** ([mdrpi:RegistrationInfo](https://docs.oasis-open.org/security/saml/Post2.0/saml-metadata-rpi/v1.0/saml-metadata-rpi-v1.0.pdf))
   - Registration authority (from federation configuration)
   - Registration instant (current timestamp)
   - Registration policy URL(s)

2. **UI Information** ([mdui:UIInfo](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-metadata-ui/v1.0/sstc-saml-metadata-ui-v1.0.pdf))
   - Display name (from entity name)
   - Description (from entity description)
   - Logo URL (from stored logo file)
   - Information URL (SP only)
   - Privacy Statement URL (SP only)

3. **Entity Attributes** ([mdattr:EntityAttributes](https://docs.oasis-open.org/security/saml/Post2.0/sstc-metadata-attr.pdf))
   - [REFEDS Research & Scholarship](https://refeds.org/category/research-and-scholarship) (R&S) category
   - [REFEDS Code of Conduct](https://refeds.org/category/code-of-conduct) (CoCo) - SP only
   - [REFEDS Sirtfi Framework](https://refeds.org/sirtfi) (Security Incident Response Trust Framework for Federated identity)

4. **Organization Information** ([md:Organization](https://docs.oasis-open.org/security/saml/v2.0/saml-metadata-2.0-os.pdf))
   - Organization name
   - Organization URL
   - Organization display name

5. **Contact Persons** ([md:ContactPerson](https://docs.oasis-open.org/security/saml/v2.0/saml-metadata-2.0-os.pdf))
   - Technical contact (name and email)
   - Security contact (for Sirtfi-compliant entities)

6. **Scope Element** (IdP only)
   - Ensure `shibmd:Scope` is present and matches the validated scope ([shibmd:Scope](https://shibboleth.atlassian.net/wiki/spaces/SC/pages/1843888238/ShibMetaExt))

The transformed metadata is saved as `{original-filename}-transformed.xml`.

## Metadata Aggregation

The system regenerates the federation metadata aggregate both on-demand and on a scheduled basis:

### Synchronous Regeneration

When entities are created, updated, or deleted through the admin interface, the system synchronously transforms and regenerates federation metadata as part of the request flow.

Entity create/edit operations must complete transformation before beta metadata is regenerated. If transformation fails, the user sees an error and beta regeneration is skipped.

Before an entity can be submitted for approval, FedAdmin checks that its transformed metadata file exists and is not older than the uploaded source metadata. This prevents approval from proceeding with missing or stale transformed metadata.

When member organization or federation information is modified, the system synchronously re-transforms the affected entities except eduGAIN `ALREADY_IN` records, and regenerates federation metadata only if every transformation succeeds. If any transformation fails, the failed entities are reported and regeneration is skipped.

Metadata regeneration failures are reported to the user. Approval and withdrawal operations keep the entity in its original status if production metadata cannot be regenerated. For beta-only changes such as entity create, edit, or delete, the data change may already be saved, but the user is told that beta metadata was not regenerated and should retry after the generation issue is fixed or contact a federation administrator.

### Scheduled Regeneration

For regular metadata maintenance and compliance with eduGAIN requirements, the system can also regenerate metadata on a scheduled basis. See [Scheduled Tasks](../deployment/scheduled_tasks.md) for details on configuring automated metadata regeneration.
