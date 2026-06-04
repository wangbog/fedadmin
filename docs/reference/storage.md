# Storage

## Federation Storage

The `storage/` directory is created at runtime and is not included in the project repository via `.gitignore`. Files are automatically organized by organization ID.

```text
storage/
|-- public/                            # Public files
|   |-- members/                       # Public member files
|   |   `-- {organization_id}/         # Public member files for this member
|   |       `-- ...                    # Reserved: public files for this member
|   `-- federation/                    # Public federation files
|       |-- fed-metadata.xml           # Production metadata: READY status entities
|       |-- fed-metadata-edugain.xml   # eduGAIN metadata: READY status entities with eduGAIN participation enabled
|       `-- fed-metadata-beta.xml      # Beta metadata: entities in INIT or APPROVING status
`-- private/                           # Protected files (with access controlled)
    |-- members/                       # Protected member files
    |   `-- {organization_id}/         # Protected member files for this member
    |       |-- idp-{idp_id}-metadata.xml              # IdP entity metadata (uploaded by administrator user)
    |       |-- idp-{idp_id}-metadata-transformed.xml  # With federation-specific extensions (e.g., mdui)
    |       |-- sp-{sp_id}-metadata.xml                # SP entity metadata (uploaded by administrator user)
    |       |-- sp-{sp_id}-metadata-transformed.xml    # With federation-specific extensions (e.g., mdui)
    |       `-- ...                                    # Other private files for this member
    `-- federation/                    # Protected federation files
        |-- fed.crt                    # X.509 certificate (share for signature verification)
        `-- fed.key                    # Private key (SECRET - never share, keep permissions restricted)
```

> **Security Warning:** The private key (`fed.key`) is critical for signing federation metadata. Ensure it is stored securely with restricted permissions (600) and never exposed to unauthorized users. If compromised, regenerate certificates immediately using `flask init-certs`, and don't forget to exchange the new certificate with eduGAIN.

## Database

The application uses SQLite for data storage:

- **Development**: `./instance/fedadmin-dev.db` (host) -> `/app/instance/fedadmin-dev.db` (container)
- **Production**: `./data/instance/fedadmin-prod.db` (host) -> `/app/instance/fedadmin-prod.db` (container)
