<!--
Sync Impact Report:
- Version: Initial (template) → 1.0.0 (first ratification)
- Modified principles: All principles defined from template
- Added sections: Code Quality Standards, Development Workflow
- Templates updated:
  ✅ plan-template.md - Constitution Check aligned with PEP8 principles
  ✅ spec-template.md - Requirements include code quality criteria
  ✅ tasks-template.md - Tasks include linting and type checking validation
- Follow-up TODOs: None
-->

# jpstock-watchlist Constitution

## Core Principles

### I. PEP8 Compliance (NON-NEGOTIABLE)

All Python code MUST strictly follow PEP8 style guidelines:
- Code MUST pass `ruff check` with zero warnings
- Line length MUST NOT exceed 88 characters (Black-compatible)
- Import ordering MUST follow isort conventions (stdlib → third-party → local)
- Naming conventions MUST be enforced: snake_case for functions/variables, PascalCase for classes
- Docstrings MUST use Google or NumPy style for all public functions and classes

**Rationale**: PEP8 ensures consistent, readable code across the team. Automated enforcement via ruff prevents style debates and speeds up code review.

### II. Type Safety (NON-NEGOTIABLE)

Strong typing MUST be enforced across all code:
- All function signatures MUST include type hints for parameters and return values
- Pydantic models MUST be used for data validation and serialization
- Code MUST pass `pyright` type checking in strict mode with zero errors
- No use of `Any` type without explicit justification and `# type: ignore` comments

**Rationale**: Type safety catches bugs at development time, improves IDE support, and serves as inline documentation.

### III. Automated Quality Gates

Code quality MUST be validated automatically before commits:
- Lefthook MUST run pre-commit hooks for linting (ruff) and type checking (pyright)
- All checks MUST pass before code can be committed
- CI/CD pipelines MUST enforce same checks on pull requests
- Formatting MUST be automated via `ruff format` (no manual formatting)

**Rationale**: Automated enforcement ensures consistency and prevents regressions. Pre-commit hooks catch issues before they reach code review.

### IV. Dependency Management

Project dependencies MUST be managed through modern Python tooling:
- `uv` MUST be used for fast, reliable dependency resolution and installation
- `mise` MUST manage Python versions and development tools
- All dependencies MUST be pinned in `pyproject.toml` with version constraints
- Development dependencies MUST be separated from runtime dependencies

**Rationale**: Modern tooling (uv, mise) provides faster installs, better reproducibility, and simplified environment management.

### V. Test-First Development

Testing MUST follow TDD principles where applicable:
- Unit tests MUST be written for all business logic
- Tests MUST use type hints and pass pyright checks
- Test coverage goals SHOULD be established per-feature
- Integration tests MUST validate Pydantic models and API contracts

**Rationale**: Tests serve as executable documentation and prevent regressions. Type-checked tests ensure test reliability.

## Code Quality Standards

All code MUST meet these quality criteria:

- **Formatting**: Automated via `ruff format` (88-character line length, Black-compatible)
- **Linting**: Zero warnings from `ruff check` with enabled rule sets: E (pycodestyle errors), F (pyflakes), I (isort), N (pep8-naming), UP (pyupgrade)
- **Type Checking**: Zero errors from `pyright` in strict mode
- **Validation**: Pydantic models for all data structures requiring validation
- **Documentation**: Docstrings required for all public APIs (functions, classes, modules)

## Development Workflow

### Environment Setup

1. Install mise: `curl https://mise.run | sh`
2. Install tools: `mise install` (installs Python, uv, ruff, lefthook from mise.toml)
3. Install dependencies: `uv sync` (creates venv and installs from pyproject.toml)
4. Setup hooks: `lefthook install` (configures pre-commit hooks)

### Development Cycle

1. Write/update code with proper type hints
2. Run formatter: `ruff format .`
3. Fix linting issues: `ruff check --fix .`
4. Verify types: `pyright`
5. Run tests (when applicable)
6. Commit (lefthook runs pre-commit checks automatically)

### Code Review Requirements

- All automated checks MUST pass (verified by CI/CD)
- Type hints MUST be comprehensive and accurate
- Pydantic models MUST be used for structured data
- PEP8 compliance MUST be verified (via ruff)
- No `# type: ignore` or `# noqa` comments without documented justification

## Governance

This constitution supersedes all other coding practices and style guides. The automated tooling configuration (ruff, pyright, lefthook) serves as the executable specification of these principles.

### Amendment Process

- Constitution changes MUST be versioned following semantic versioning
- MAJOR: Breaking changes to core principles or tool configurations
- MINOR: New principles added or expanded guidance
- PATCH: Clarifications, typo fixes, non-semantic updates

### Compliance Verification

- Pre-commit hooks enforce compliance at commit time
- CI/CD pipelines MUST run full validation suite
- All violations MUST be fixed before merge
- Complexity that violates principles MUST be justified in code review

**Version**: 1.0.0 | **Ratified**: 2025-12-07 | **Last Amended**: 2025-12-07
