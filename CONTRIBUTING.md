# Contributing to sih_website_status

Thank you for considering a contribution.

## Before you start

- Read the project README and relevant design or security documentation.
- Check existing issues and pull requests before starting duplicate work.
- For substantial changes, discuss the proposed scope before implementation.
- Keep pull requests focused and explain user impact, design trade-offs, and compatibility implications.

## Development setup

Follow the prerequisites and setup instructions in README.md.

## Validation

Install with npm ci when a lockfile exists (otherwise npm install). Use the scripts declared in package.json. Run available lint, typecheck, test scripts and npm run build before submitting.

Add or update tests for behavior changes. Document configuration, migration, operational, and security implications. Do not claim a test passed unless you ran it and observed a successful result.

## Pull request checklist

- [ ] The change has a clear problem statement and bounded scope.
- [ ] Tests cover changed behavior and relevant regressions.
- [ ] Documentation and examples are updated.
- [ ] No credentials, private data, generated artifacts, or machine-specific paths are included.
- [ ] Security, privacy, accessibility, and performance implications are considered.
- [ ] The PR describes validation commands and their actual results.

Use descriptive commits such as feat, fix, docs, test, refactor, security, and chore. Follow CODE_OF_CONDUCT.md.
