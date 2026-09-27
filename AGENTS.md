# codex-headless-skill

A Claude Code plugin that makes `codex exec` (OpenAI Codex CLI headless mode) an execution
backend, with Claude orchestrating and Codex implementing.

## Workflow for every change

Every change goes through a branch and a pull request. Whether it also needs a
GitHub issue depends on whether it needs tracking.

**Open an issue for:**
- every `feat`
- every breaking change
- a fix that is large or complicated
- anything someone raised, whether the user or another agent session

**No issue needed for:** a small patch or a small fix that nobody raised. Go
straight to step 2.

1. **Issue first, when one is needed.** Before writing any code, open a GitHub
   issue that states the request: what is wanted, the decisions already made,
   and the facts that were checked. If the request came from someone else, say
   who it came from.
2. **Branch.** Branch off an up-to-date `main` (`git pull --rebase` first). Name the
   branch `<type>/<short-slug>`, for example `feat/advise-skill`. Never commit to
   `main` directly.
3. **Work and verify.** Commit with Conventional Commits:
   `<type>(<scope>): <summary>`. Before opening the PR, run
   `claude plugin validate . --strict` and the test suite.
4. **Pull request.** Run `git pull --rebase origin main`, push, then open the PR
   with `gh pr create`. When there is an issue, the PR body must contain
   `Closes #<issue>` so the PR is linked to it. The PR title becomes the squash commit, and release-please
   reads it, so it must follow Conventional Commits.
5. **Merge and close.** Squash-merge with `gh pr merge <n> --squash --delete-branch`.
   If there is an issue, the `Closes` line closes it. Check it with
   `gh issue view <n>`, and close it by hand with a comment if it is still open.

A bug found while working on something else gets its own PR, never a fix inside
the unrelated one. It gets an issue too if it is large or complicated.

## Agent skills

### Issue tracker

Issues live as GitHub issues in `GauranshMathur/codex-headless-skill`, driven via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` and one `docs/adr/` at the repo root. See `docs/agents/domain.md`.
