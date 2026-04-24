# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest release | ✅ |
| Older releases | ❌ |
| Development / PR branches | best effort only |

Always update to the latest release before reporting a vulnerability.

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report them privately via **GitHub Security Advisories**:

👉 [Report a vulnerability](https://github.com/AlexRosbach/AutoDoku/security/advisories/new)

### What to include

- Affected version of AutoDoku
- Windows version and environment
- Step-by-step reproduction instructions
- Potential impact / what an attacker could achieve
- Logs, screenshots, or proof-of-concept (redact real passwords and tokens)

### What to expect

After you submit a report:

1. Quick acknowledgement of receipt
2. Severity assessment and scope confirmation
3. Fix or mitigation plan shared with you
4. Public disclosure only after a fix is available and users have had time to update

---

## Scope

### In scope

- Credential exposure (stored WMI / SSH / SNMP credentials)
- Privilege escalation via scan results or the UI
- Remote code execution triggered by crafted network responses
- Injection vulnerabilities (CSV injection, command injection)
- Insecure defaults with real-world security impact

### Out of scope

- Best-practice suggestions without an exploit path
- Missing hardening recommendations only (no demonstrated impact)
- Vulnerabilities in unsupported or heavily modified deployments
- Denial-of-service requiring unrealistic resources

---

## Handling sensitive data

When submitting a report, please **do not include** real passwords, API tokens,
private keys, or production credentials. Use redacted examples instead.
