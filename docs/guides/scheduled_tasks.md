# Scheduled Tasks

The FedAdmin system includes automated scheduled tasks for maintenance and metadata management. These tasks are defined in `app/__init__.py` and help ensure the federation operates smoothly and remains compliant with external requirements.

## Overview

The system currently implements two main scheduled tasks:

1. **Regenerate Metadata Job** - Daily metadata generation to maintain compliance with eduGAIN requirements
2. **Check eduGAIN Updates Job** - Configurable monitoring of entities already in eduGAIN

For system administrators, these tasks run automatically in the background using APScheduler. The tasks are configured to handle potential misfires and ensure consistent operation even if the system experiences temporary downtime.

## Regenerate Metadata Job

The Regenerate Metadata Job is responsible for creating and updating the federation's metadata files on a scheduled basis.

### Functionality

- **Purpose**: Generates the three federation metadata files at scheduled intervals
- **Primary Reason**: eduGAIN requires federation metadata `validUntil` attribute not to exceed 28 days. This job updates the `validUntil` timestamp to maintain compliance.
  - Reference: [eduGAIN Technical Guidelines](https://wiki.refeds.org/display/EG/eduGAIN+Technical+Guidelines)

### Configuration

The job can be configured via environment variables in your `.env` file:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `METADATA_REGENERATION_TIME` | Time for daily metadata regeneration (UTC). Format: "hour:minute" | `"2:00"` |
| `METADATA_REGENERATION_MISFIRE_GRACE_TIME` | Grace time in seconds for metadata regeneration tasks before they are skipped | `60` |

### Trigger

- **Schedule**: Daily execution at the time specified by `METADATA_REGENERATION_TIME`
- **Syntax**: Standard cron format, but configured through environment variables

### Process Details

1. **Source Collection**
   - Collects transformed metadata files from all entities
   - Filters by entity status (INIT, APPROVING, READY)
   - May optionally filter by eduGAIN participation based on configuration

2. **pyFF Pipeline Processing**
   - Load all source metadata files into the pyFF processing pipeline
   - Select relevant EntityDescriptor elements
   - Apply XSLT transformation for federation-specific formatting
   - Finalize with federation metadata attributes:
     - `ID`: Federation ID with timestamp
     - `Name`: Federation name URN
     - `validUntil`: Set to 28 days from current time to ensure compliance

3. **Digital Signing**
   - Sign the aggregated metadata using the federation's X.509 certificate
   - Generate XML Signature according to [XML-Signature Syntax and Processing](https://www.w3.org/TR/xmldsig-core/)
   - The certificate is stored in `storage/private/federation/fed.crt`

4. **Output Generation**
   The job generates three distinct metadata files:

   - **Production metadata** (`storage/public/federation/federation-metadata.xml`):
     - Contains all approved entities (status = READY)
     - Used for production federation operations
     - Signed with federation certificate
   
   - **eduGAIN metadata** (`storage/public/federation/fed-metadata-edugain.xml`):
     - Contains only approved entities (status = READY) with eduGAIN enabled
     - Used for interoperability with the international eduGAIN federation
     - Entities included: `idp_edugain = YES` or `sp_edugain = YES`
   
   - **Beta metadata** (`storage/public/federation/fed-metadata-beta.xml`):
     - Contains entities pending approval (status = INIT or APPROVING)
     - Used for testing and preview before official approval
     - Allows federation administrators to review metadata before entities go live

### Troubleshooting

If the metadata regeneration fails:

1. Check logs in your application console for specific error messages
2. Verify that all entity metadata files are properly formatted and valid
3. Ensure the federation certificate is present and accessible
4. Confirm pyFF dependencies are installed and up-to-date

## Check eduGAIN Updates Job

The Check eduGAIN Updates Job ensures that entities already part of eduGAIN remain synchronized with the international federation.

### Functionality

- **Purpose**: Monitors and updates metadata for entities already in eduGAIN
- **Goal**: Ensures synchronization with international eduGAIN federation
- **Method**: Uses SHA1 comparison to detect changes in eduGAIN metadata

### Configuration

The eduGAIN check interval can be configured via the environment variable:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `EDUGAIN_CHECK_INTERVAL` | Time interval for checking eduGAIN updates (hours) | `1` |

### Trigger

- **Schedule**: Configurable interval execution based on `EDUGAIN_CHECK_INTERVAL` setting
- **Syntax**: Configured via APScheduler with interval (e.g., `*/1` for hourly, `*/2` for every 2 hours)

### Process Details

1. **Entity Identification**
   - Identify all entities with `ALREADY_IN` status in eduGAIN
   - These entities have their metadata automatically synchronized with eduGAIN

2. **Change Detection**
   - Retrieve current metadata from eduGAIN's public API for each entity
   - Compare using SHA1 hash of the metadata content
   - If hashes differ, an update is required

3. **Local Update**
   - Download and validate the updated metadata from eduGAIN
   - Store in local storage (`storage/private/members/{org_id}/`)
   - Apply federation-specific transformations as needed

4. **Federation Metadata Regeneration**
   - If updates were made, trigger the metadata regeneration process
   - This ensures the federation metadata files include the latest information

5. **Statistics and Reporting**
   - Maintain a log of updated entities
   - Provide statistics on the number of entities requiring updates
   - Report any errors encountered during the synchronization process

### Benefits

- **Automatic Synchronization**: Maintains metadata consistency without manual intervention
- **Reduced Administrative Overhead**: Eliminates need for manual checks and updates
- **Improved Accuracy**: Ensures local metadata matches the official eduGAIN source
- **Error Detection**: Identifies when entities are removed from eduGAIN or changed
- **Configurable Frequency**: Adjust check interval based on federation needs

### Troubleshooting

If the eduGAIN check fails:

1. Verify network connectivity to eduGAIN's API endpoints
2. Check the status of eduGAIN services (refeds.org)
3. Ensure EntityIDs are correctly formatted and registered in eduGAIN
4. Review logs for specific error messages related to API calls or validation
5. Confirm the `EDUGAIN_CHECK_INTERVAL` is set to a reasonable value

## Common Configuration

Both scheduled tasks can be configured through environment variables in your `.env` file:

```bash
# Metadata Regeneration Configuration
METADATA_REGENERATION_TIME=2:00
METADATA_REGENERATION_MISFIRE_GRACE_TIME=60

# eduGAIN Check Configuration
EDUGAIN_CHECK_INTERVAL=1
```

## Security Considerations

- All generated metadata files are digitally signed using the federation's X.509 certificate
- The private key used for signing is stored separately and should have restricted permissions (600)
- Regular certificate rotation is recommended to maintain security
- Metadata files are stored in public directories but are still protected by the digital signature

## Monitoring and Maintenance

- Regularly monitor logs to ensure scheduled tasks are running correctly
- Set up alerts for task failures or missed executions
- Consider implementing a dashboard for visualizing task execution statistics
- Keep dependencies (pyFF, lxml, etc.) updated to benefit from bug fixes and security patches
- Adjust `EDUGAIN_CHECK_INTERVAL` based on federation size and update frequency requirements

For more information about the SAML metadata processing pipeline and storage structure, refer to the main [README.md](../../README.md#saml-metadata-processing) document.