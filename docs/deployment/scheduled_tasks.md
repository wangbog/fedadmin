# Scheduled Tasks

TODO - whole page

The FedAdmin system includes automated scheduled tasks for maintenance and metadata management. These tasks are configured using system cron and Flask CLI commands.

## Overview

The system implements two main scheduled tasks:

1. **Regenerate Metadata Job** - Daily metadata generation to maintain compliance with eduGAIN requirements
2. **Check eduGAIN Updates Job** - Configurable monitoring of entities already in eduGAIN

These tasks are executed using system cron rather than APScheduler to avoid dependency conflicts and ensure reliability. The actual metadata regeneration uses file locks to prevent concurrent execution.

## Architecture

### Why Cron Instead of APScheduler?

- **No dependency conflicts**: Avoids APScheduler version incompatibility issues
- **System-level reliability**: Cron is a robust system component that won't crash with Python errors
- **Simplicity**: No need to manage Python job stores or database tables
- **File locks**: The metadata regeneration already uses `portalocker` for concurrency control

### Task Execution Flow

```
Cron Daemon → Flask CLI Command → App Context → MetadataService → File Lock → Execution → Result Logging
```

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

### Trigger

- **Schedule**: Daily execution at the time specified by `METADATA_REGENERATION_TIME`
- **Command**: `flask regenerate-metadata`

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

### Manual Execution

You can manually trigger the metadata regeneration:

```bash
flask regenerate-metadata
```

This will regenerate all three metadata files synchronously and display the result.

## Check eduGAIN Updates Job

The Check eduGAIN Updates Job ensures that entities already part of eduGAIN remain synchronized with the international federation.

### Functionality

- **Purpose**: Monitors and updates metadata for entities already in eduGAIN
- **Goal**: Ensures synchronization with international eduGAIN federation
- **Method**: Uses SHA1 comparison to detect changes in eduGAIN metadata

### Configuration

The eduGAIN check interval can be configured via environment variable:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `EDUGAIN_CHECK_INTERVAL` | Time interval for checking eduGAIN updates (hours) | `1` |

### Trigger

- **Schedule**: Configurable interval execution based on `EDUGAIN_CHECK_INTERVAL` setting
- **Command**: `flask check-edugain-updates`

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

### Manual Execution

You can manually trigger the eduGAIN updates check:

```bash
flask check-edugain-updates
```

This will check for updates and display statistics.

## Cron Configuration

### Production Environment

Add the following lines to your system crontab (usually `/etc/cron.d/fedadmin`):

```bash
# Regenerate metadata daily at 2:00 AM UTC
0 2 * * * cd /path/to/fedadmin && flask --app run regenerate-metadata >> /var/log/fedadmin/cron.log 2>&1

# Check eduGAIN updates every hour
0 */1 * * * cd /path/to/fedadmin && flask --app run check-edugain-updates >> /var/log/fedadmin/cron.log 2>&1
```

### Development Environment

Add the following lines to your system crontab:

```bash
# Regenerate metadata daily at 2:00 AM and 2:00 PM
0 2,14 * * * cd /path/to/fedadmin && flask --app run regenerate-metadata >> /tmp/fedadmin-cron.log 2>&1

# Check eduGAIN updates every 2 hours
0 */2 * * * cd /path/to/fedadmin && flask --app run check-edugain-updates >> /tmp/fedadmin-cron.log 2>&1
```

### Note on App Context

When running Flask CLI commands via cron, use `flask --app run <command>` to ensure the correct app context is loaded.

### Log Files

Make sure the log directories exist and have proper permissions:

```bash
mkdir -p /var/log/fedadmin
chown fedadmin:fedadmin /var/log/fedadmin
chmod 640 /var/log/fedadmin/cron.log
```

## User-Triggered Tasks

When you click the "Regenerate Metadata" button in the admin interface, the task is now executed **synchronously** instead of asynchronously. This means:

- You will see a loading indicator while the task is processing
- The page will redirect to the success/error message after completion
- No task queue or background scheduler is involved
- File locks still prevent concurrent execution if multiple admins trigger the task simultaneously

This change was made to simplify the codebase and avoid APScheduler dependencies.

## Security Considerations

- All generated metadata files are digitally signed using the federation's X.509 certificate
- The private key used for signing is stored separately and should have restricted permissions (600)
- Regular certificate rotation is recommended to maintain security
- Metadata files are stored in public directories but are still protected by the digital signature
- Cron jobs should run as the same user as the application to ensure proper file access

## Troubleshooting

### Cron Jobs Not Running

1. Check cron service is enabled:
   ```bash
   sudo systemctl status cron
   sudo systemctl enable cron
   ```

2. Check cron logs:
   ```bash
   sudo tail -f /var/log/syslog | grep CRON
   ```

3. Verify the command path:
   ```bash
   which flask
   ```

### Task Fails to Execute

1. Test the command manually:
   ```bash
   flask --app run regenerate-metadata
   ```

2. Check for file lock conflicts:
   ```bash
   ls -la /tmp/fedadmin-metadata.lock
   ```

3. Review application logs:
   ```bash
   tail -f /var/log/fedadmin/app.log
   ```

### Manual Metadata Regeneration

If you need to regenerate metadata immediately (e.g., after making changes):

1. Click "Regenerate Metadata" button in the admin interface
2. Or run: `flask --app run regenerate-metadata`
3. Wait for completion and verify the generated files

## Monitoring and Maintenance

- Regularly monitor cron logs to ensure tasks are running correctly
- Set up alerts for task failures or missed executions
- Keep dependencies (pyFF, lxml, etc.) updated to benefit from bug fixes and security patches
- Adjust `EDUGAIN_CHECK_INTERVAL` based on federation size and update frequency requirements
- Monitor disk space for metadata files and logs

For more information about the SAML metadata processing pipeline and storage structure, refer to the main [README.md](../../README.md#saml-metadata-processing) document.