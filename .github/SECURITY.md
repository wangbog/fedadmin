# Security Policy

FedAdmin manages federation metadata, member accounts, administrative roles, and related operational data. Please report security issues privately.

## Reporting a Vulnerability

Do not open a public GitHub issue for suspected vulnerabilities.

Please contact the maintainers through a private channel, or use GitHub's private vulnerability reporting feature if it is enabled for this repository. Include:

- A short description of the issue
- Steps to reproduce the issue
- The affected version or commit
- Any relevant logs, screenshots, or proof of concept details

Avoid including real secrets, private keys, production metadata, session cookies, or password setup/reset links in reports.

## Sensitive Data

Treat password setup/reset links as credential-equivalent one-time links. Share them only with the intended user through a trusted channel.

Production `.env` files, federation signing keys, private member metadata, database files, and logs may contain sensitive information and should not be committed.
