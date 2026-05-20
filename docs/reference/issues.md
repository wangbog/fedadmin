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
