# Changelog

## 1.5.0

### Added

- `createClient` now accepts an optional `onRetry` callback that fires before
  every retry attempt with the attempt number and the triggering error.
- `computeBackoff` gained an optional `cap` parameter so callers can clamp the
  maximum delay independently of the multiplier growth.
- New `isRetryableStatus` helper exported from the package root.

### Changed

- The default `maxRetries` was raised from `3` to `5` to better match the
  retry budgets used by most upstream services. Callers that relied on the old
  value should pass `maxRetries: 3` explicitly.
- The default backoff `factor` is now `2` (previously `1.5`) for a more
  conventional exponential curve.
- Header normalization was refactored into its own module and now lower-cases
  keys consistently before they are merged with per-request overrides.

### Fixed

- `computeBackoff` no longer returns a negative delay when `attempt` is `0`.
- Retry-After parsing now tolerates whitespace around the numeric value.
