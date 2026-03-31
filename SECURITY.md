# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do NOT open a public issue.**

Instead, email **hs.ze.lab@gmail.com** with:

1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a timeline for a fix.

## Scope

This project processes LLM outputs. Security concerns include:

- **Prompt injection** via SOUL.md or debate topics
- **Cost guard bypass** allowing unbounded API spend
- **Adapter credential leakage** through logs or error messages
- **Malicious constitution rules** that override safety constraints

## Best Practices

- Never commit API keys. Use environment variables.
- Review SOUL.md files before loading untrusted constitutions.
- Set cost guard limits when using real LLM adapters.
