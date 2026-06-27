# Billing module conventions

Agreed standards for this package. Enforced in CI; violations fail the build.

## Naming

- All functions and locals use descriptive `snake_case`.
- Placeholder identifiers are forbidden: `temp`, `data`, `foo`, `util2`, `helper2`.
  A function whose purpose cannot be named without a numeric suffix does not
  belong in this module. CI greps for these tokens and fails the job.

## Boundaries

- `billing/` is core domain logic. It must not import from any transport,
  serialization, or presentation layer.
