# Security Policy

## Supported Versions

The following versions of Medication Tracker are currently supported with security updates:

| Version    | Supported          |
| ---------- | ------------------ |
| latest     | :white_check_mark: |
| < latest   | :x:                |

*Note: This project follows a rolling release model. Only the latest version receives security updates.*

## Important Security Notice

⚠️ **This application has no built-in access protection and is designed for personal use only.**

**Critical Security Recommendations:**
- **Never expose this application to the public internet**
- Deploy only on trusted local networks
- Use behind a reverse proxy with authentication if remote access is needed
- Regularly backup your data from the `/app/data` directory
- Use a strong, unique `SECRET_KEY` environment variable in production
- Monitor access logs in the `/app/logs` directory

## Reporting a Vulnerability

If you discover a security vulnerability in Medication Tracker, please help us keep the project secure by reporting it responsibly.

### How to Report
**Use GitHub Security Advisories**: [Report a vulnerability](https://github.com/Skjall/medication-tracker/security/advisories/new)

GitHub Security Advisories provide a secure, private channel for reporting vulnerabilities and allow for coordinated disclosure. This is the preferred method for all security reports.

### Alternative Contact
If you cannot use GitHub Security Advisories, you may contact the maintainer directly for critical vulnerabilities, but please avoid posting security issues in public GitHub issues or discussions.

### What to Include
Please provide as much information as possible:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Suggested fix (if you have one)
- Affected versions (if known)

### Response Timeline
- **Acknowledgment**: Within 48 hours of report
- **Initial Assessment**: Within 1 week
- **Status Updates**: Weekly until resolved
- **Resolution**: Target 30 days for critical issues, 90 days for others

### What to Expect
- **Accepted vulnerabilities**: Will be fixed in the next release with credit given to the reporter
- **Declined reports**: Will receive an explanation of why the issue doesn't qualify as a security vulnerability
- **Coordination**: We'll work with you on responsible disclosure timing through the GitHub Security Advisory process

## Security Best Practices for Users

When deploying Medication Tracker:

1. **Network Security**
   - Use only on trusted local networks
   - Consider VPN access for remote use
   - Implement firewall rules to restrict access

2. **Data Protection**
   - Regularly backup the `/app/data` directory
   - Ensure backup storage is secure
   - Consider encrypting sensitive data at rest

3. **Container Security**
   - Keep Docker and base images updated
   - Use Docker secrets for sensitive environment variables
   - Run containers with non-root users when possible

4. **Monitoring**
   - Review application logs regularly
   - Monitor for unusual access patterns
   - Set up alerts for failed access attempts

## Scope

This security policy covers:
- The main application code
- Docker container configuration
- Documentation and setup instructions

This policy does not cover:
- Third-party dependencies (report to respective maintainers)
- User-specific deployment configurations
- Infrastructure security (user responsibility)

---

*Last updated: 28th May 2025*