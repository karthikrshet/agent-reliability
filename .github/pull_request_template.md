## Description
<!-- Provide a clear, concise summary of the changes introduced by this PR. -->

## Related Issues
<!-- Reference any related issue(s) here, e.g. Fixes #123 -->

## Architectural Checklist
- [ ] Conforms to strict typing (`mypy packages apps adapters environments` passes with 0 errors)
- [ ] Conforms to code formatting & linting (`ruff check .` and `ruff format --check .` pass)
- [ ] Maintains test coverage >= 85% (`pytest -v --cov --cov-fail-under=85`)
- [ ] Scenarios validate against JSON Schema 2020-12
- [ ] Fail-closed safety invariants preserved (no security or sandbox bypasses)
- [ ] No secrets, API keys, or raw authentication tokens logged or committed
- [ ] No private model chain-of-thought stored or exposed (observable trajectory only)

## Verification Evidence
<!-- Provide terminal output or reproduction commands showing tests passing. -->
```shell
$ pytest -v
```
