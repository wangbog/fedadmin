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

## Metadata Transformation

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

## Metadata Aggregation

The system regenerates the federation metadata aggregate both on-demand and on a scheduled basis:

### Synchronous Regeneration

When entities are created, updated, or deleted through the admin interface, the system synchronously regenerate the metadata . 

TODO