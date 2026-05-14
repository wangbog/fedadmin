# Known Issues

This document describes known issues with the FedAdmin system that are currently affecting functionality or may cause future problems.

## 1. pyFF Integration Method

Currently, pyFF is invoked using the subprocess method for federation metadata aggregation and signing. We have not been able to successfully use pyFF's API for these operations. Here's a comparison of the two approaches:

**Subprocess Method:**
- **Advantages:**
  - Simple to implement and debug
  - No need to understand pyFF's internal API
  - Easy to pass configuration files
  - Better isolation from pyFF's internal state
- **Disadvantages:**
  - Higher overhead due to process creation
  - Less control over pyFF's internal operations
  - Harder to handle errors and exceptions
  - Limited ability to monitor progress

**API Method:**
- **Advantages:**
  - Lower overhead and faster execution
  - Direct access to pyFF's internal operations
  - Better error handling and exception management
  - Ability to monitor and control pyFF's state
- **Disadvantages:**
  - More complex implementation
  - Requires understanding of pyFF's internal API
  - Potential for tighter coupling with pyFF's implementation
  - More difficult to debug

## 2. OpenSSL dependency

pyFF depends on OpenSSL for digital signing operations. This means both development and production environments must use Linux, as OpenSSL is not fully supported on Windows. Since this project uses Docker containers for both development and production, the Linux requirement is satisfied by the container environment.

## 3. APScheduler pkg_resources Deprecation Warning

**Root Cause:**
This project uses `pyFF==2.1.5` which has a hard dependency on **APScheduler 3.6.3**, an older version released in 2020. This version of APScheduler directly imports the now deprecated `pkg_resources` API during module initialization.

This warning appears in the console whenever any Flask command is executed (including `flask init-certs`, `flask init-db`, or when starting the application server) as soon as pyFF is imported:

```
/usr/local/lib/python3.12/site-packages/apscheduler/__init__.py:1: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  from pkg_resources import get_distribution, DistributionNotFound
```

**Current Status:**
✅ This warning does **not** affect functionality. The application operates normally.
⚠️ This is a future compatibility warning: Setuptools will completely remove the `pkg_resources` module on or after **2025-11-30**, at which point this version of APScheduler will fail to initialize.
🔒 Dependencies are currently locked. Upgrading APScheduler will break pyFF's scheduled task functionality.

This issue will need to be addressed when a compatible updated version of pyFF becomes available.