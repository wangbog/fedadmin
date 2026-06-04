# Scheduled Tasks

FedAdmin includes automated scheduled tasks for metadata management. These tasks can be triggered manually via Flask CLI commands or configured via system cron.

## Overview

The system implements two main scheduled tasks:

1. **Regenerate Metadata Job** - Regenerates federation metadata files with updated `validUntil` timestamps
2. **Check eduGAIN Updates Job** - Monitors entities already in eduGAIN for synchronization

## Task Commands

### Regenerate Metadata

Regenerates all three federation metadata files (`fed-metadata-beta.xml`, `fed-metadata.xml`, `fed-metadata-edugain.xml`).

**Command:**
```bash
flask regenerate-metadata
```

**Output:** Shows "Metadata regeneration completed successfully!" when complete

### Check eduGAIN Updates

Checks for updates to entities already in eduGAIN and synchronizes if changes are detected.

**Command:**
```bash
flask check-edugain-updates
```

**Output:** Shows update statistics, e.g., `eduGAIN update check completed: {'checked': 10, 'updated': 1, 'unchanged': 9, 'errors': 0}`

## Task Details

### Regenerate Metadata Job

- **Purpose:** Regenerates federation metadata files with updated `validUntil` timestamps (28-day validity per eduGAIN requirements). According to the [eduGAIN SAML profile](https://technical.edugain.org/doc/eduGAIN-saml-profile.pdf), the metadata must include a `validUntil` attribute with a value not later than 28 days after the creationInstant. If the federation's IdP/SP entities do not change frequently and no Regenerate Metadata operation is triggered within 28 days, the federation's metadata will expire and fail compliance checks. This scheduled task ensures regular metadata regeneration (typically daily) to maintain valid metadata and comply with eduGAIN requirements.
- **Files Regenerated:**
  - `fed-metadata-beta.xml`: Entities in `INIT` or `APPROVING` status
  - `fed-metadata.xml`: `READY` status entities
  - `fed-metadata-edugain.xml`: `READY` status entities with eduGAIN participation enabled
- **Certificate:** Uses federation X.509 certificate at `storage/private/federation/fed.crt`

### Check eduGAIN Updates Job

- **Purpose:** Monitors entities already part of eduGAIN (with `ALREADY_IN` status) for metadata changes to ensure synchronization with the international federation. When member organization administrators add IdP/SP entities, they can select the `ALREADY_IN` option, which indicates the entity has joined eduGAIN through another federation. This means the entity's metadata may have been automatically updated by that other federation. The scheduled task periodically checks these entities against eduGAIN's metadata API to detect any updates and ensures the local federation metadata remains synchronized with the latest entity information.
- **Method:** Compares SHA1 hashes of current and eduGAIN metadata
- **Action:** Automatically updates local entity metadata if changes are detected and triggers metadata regeneration
