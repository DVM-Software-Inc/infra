# Task: GitHub Actions cost optimization (local-first CI)

Reusable agent task: point an LLM session at any DVM-Software app repo to bring its
workflows in line with the org CI cost policy (see `base.md` → "CI cost policy").
Written with macOS-heavy repos in mind (macOS runner minutes are 10× ubuntu), but the
policy applies to every repo.

## Goal

Reduce GitHub Actions cost to nearly zero during normal development. Development
testing happens locally (`./scripts/check.sh` or the repo's equivalent gate);
GitHub runners are for `main` deploys, on-demand verification, and releases only.

## Policy (non-negotiable outcomes)

1. **No automatic workflows on feature branches or pull requests — none.**
   Automatic triggers are allowed only on:
   - **push to `main`** — cheap ubuntu jobs only (lint/test/build/deploy per the
     `base.md` CI/CD contract), and
   - **release tags `v*`**.

   Everything else is `workflow_dispatch`. The intent:
   - normal commits → no GitHub runner
   - manual verification → run on demand
   - production releases → automatic

2. **Every workflow carries concurrency protection** so obsolete runs are never paid for:

   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```

3. **`runs-on: macos-*` only where macOS is genuinely required** — AppKit/Xcode
   compilation, codesigning, notarization, archive/DMG generation, simulator tests.
   Everything else migrates to `ubuntu-latest`. macOS jobs never run automatically
   on branches or PRs; they run via `workflow_dispatch` or `v*` tags only.

4. **Two logical pipelines, separated:**
   - *Development / verify* — `workflow_dispatch` only. Tests, compile, project
     health. No packaging, no notarization, no release artifacts.
   - *Release* — `workflow_dispatch` **and** `push: tags: ["v*"]`. Clean build,
     archive, codesign, notarize, package ZIP/DMG, publish artifacts. (For macOS
     repos: distribution specifics are still per-repo — see `macos.md` "Not yet
     standardized"; preserve the repo's existing release process.)

## Steps

1. **Audit** every workflow under `.github/workflows/`. For each: triggers, jobs,
   runner types, duplicated work, unnecessary macOS jobs, merge/simplify candidates.
   Produce a short summary **before** making changes.
2. **Retrigger** per the policy above (strip `push`/`pull_request` from non-`main`,
   non-tag workflows; add `workflow_dispatch`).
3. **Add the concurrency block** to every workflow.
4. **Migrate** non-macOS-requiring jobs to `ubuntu-latest`.
5. **Split** development from release pipelines as above.
6. **Deduplicate** — merge workflows doing identical work, share reusable
   actions/workflows, never build the same project twice in one run.
7. **Preserve CI quality** — unit tests, release build, linting, plist validation,
   codesign verification, and artifact validation must all still exist *somewhere*;
   the change is *when* they run, not *whether*. Do not remove functionality unless
   it is clearly redundant.
8. **Document** in `docs/CI.md`: each workflow, when it runs, how to trigger
   manually, the release process, expected Actions cost, and the rationale.
9. **Report**: files modified, workflows removed/added, estimated macOS-minute
   reduction and monthly savings, and any risks introduced.

## Guardrails

- Server-deployed repos keep the `base.md` contract untouched: push to `main` still
  auto-deploys dev via the infra reusable workflows; prod stays manual
  `workflow_dispatch`. This task removes branch/PR noise around that contract, not
  the contract itself.
- Flag deviations you can't reconcile; never silently drop a validation step.
