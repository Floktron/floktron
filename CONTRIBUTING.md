# Contributing

Ideas, bug reports and wishes are welcome — see [docs/FEEDBACK.md](docs/FEEDBACK.md).

## Code and text contributions

By sending a contribution (pull request, patch, text, prompt, template or file) you agree to these terms:

1. You grant **KOAGU ELEMENT SIA** a worldwide, perpetual, irrevocable, non-exclusive, royalty-free licence to use,
   copy, modify, publish, sublicense and relicense your contribution under any terms, including commercial licences.
2. You keep the copyright to your own contribution and may use it elsewhere.
3. You confirm the contribution is your own work, or you have the right to submit it under these terms, and it
   contains no code under a licence that conflicts with [LICENSE.md](LICENSE.md).
4. You remove passwords, personal data and client names before sending.

Why point 1 is needed: FLOKTRON is offered both under the AGPL-3.0 and under a commercial licence. KOAGU ELEMENT SIA
can do that only if it may license every part of the code, including yours, under both. Your contribution itself is
published under the AGPL-3.0 like the rest of the code.

Add this line to the pull request description:
`I agree to the contribution terms in CONTRIBUTING.md.`

## Before you send code
- Every new feature or fixed bug comes with an automated test in `tests/`; `pytest -q` and `python tests/first_run_smoke.py` must pass.
- Tests and examples use fictional companies and fictional data only.
- The security checks must stay green: `pip install -r .github/security-tools.txt`, then `bandit -r scripts -ll` and
  `pip-audit -r requirements.txt` ([docs/SECURITY_SCANS.md](docs/SECURITY_SCANS.md)). GitHub runs the same checks, plus CodeQL, on every pull request.
- No new outside package without a reason in the pull request; network code only in the files listed in [docs/TRANSPARENCY.md](docs/TRANSPARENCY.md).
