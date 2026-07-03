# Issue Implementation Prompt

You are implementing a solution for a GitHub issue.

The issue context is available at:

```text
./issue-context.json
```

Your job:

1. Read the issue context.
2. Read `README.md`.
3. Read `AGENTS.md` if it exists.
4. Inspect the repository.
5. Identify the smallest safe implementation that addresses the issue.
6. Make code changes.
7. Add or update tests when practical.
8. Avoid unrelated refactors.
9. Avoid changing public behavior beyond what the issue requires.
10. Do not touch secrets, credentials, deployment settings, or production data.
11. If the issue is ambiguous or unsafe, do not force a solution. Leave notes explaining the blocker.

Before editing, determine:

- What files are likely relevant
- What behavior needs to change
- What tests or checks should validate the fix

After editing, return a markdown summary with:

## Summary

What changed.

## Files changed

List the important files and why they changed.

## Validation

List what checks you ran or what checks should be run.

## Risks

Call out any risks, assumptions, or places needing human review.

## Follow-up

Mention anything the human maintainer should do before merging.
