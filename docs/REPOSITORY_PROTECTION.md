# Repository protection record

Record of branch protection and governance actions taken on
`kimeisele/engineering-encyclopedia`, per Section 2 and Section 11 of the
founding brief (`docs/FOUNDING BRIEF v2.md`).

## Requested (Section 2)

Protect `main` with exactly:

- pull requests required (no approval requirement — a solo owner cannot
  satisfy one)
- force pushes blocked
- deletion blocked
- required status check `validate`
- nothing else: no rulesets, no security-feature checklist, no CODEOWNERS

## Applied

`PUT /repos/kimeisele/engineering-encyclopedia/branches/main/protection`
on 2026-08-01, after the `validate` workflow had run at least once on `main`
(head `e6e8ab2`, run `30707301688`, conclusion `success`).

Read back from the API on application:

| Setting | Value |
|---|---|
| `required_status_checks.checks` | `[{"context": "validate"}]` |
| `required_status_checks.strict` | `false` |
| `required_pull_request_reviews.required_approving_review_count` | `0` |
| `required_pull_request_reviews.dismiss_stale_reviews` | `false` |
| `required_pull_request_reviews.require_code_owner_reviews` | `false` |
| `allow_force_pushes` | `false` |
| `allow_deletions` | `false` |
| `enforce_admins` | `false` |
| `required_linear_history` | `false` |
| `required_conversation_resolution` | `false` |
| `required_signatures` | `false` |

## Refused by the platform

Nothing. Every requested setting was applied on the first attempt; no
settings were silently weakened.

## Other repository settings

- Default branch: `main`
- Visibility: public
- Topics: `engineering`, `coding-agents`, `developer-tools`, `knowledge-base`,
  `python`, `yaml`
- No branch rulesets exist; protection is the single branch-protection rule
  above only.
