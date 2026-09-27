# Changelog

## [0.1.1](https://github.com/GauranshMathur/codex-headless-skill/compare/v0.1.0...v0.1.1) (2026-09-11)


### Bug Fixes

* **skill:** keep effort at high unless the user asks for another ([#3](https://github.com/GauranshMathur/codex-headless-skill/issues/3)) ([a8caac5](https://github.com/GauranshMathur/codex-headless-skill/commit/a8caac5ce664072d6fad883665a7e15b442d4efc))

## 0.1.0 (2026-09-11)


### Features

* **plugin:** add plugin manifests, the exec skill, and thread resume ([f6896b4](https://github.com/GauranshMathur/codex-headless-skill/commit/f6896b419cafbeeb80210fcd0ff8083333a01a86))
* **runner:** add the command line with --list-models and --dry-run ([77e817c](https://github.com/GauranshMathur/codex-headless-skill/commit/77e817c312de998d4f99a80043404c2b9741a2ec))
* **runner:** always pass an explicit workspace-write sandbox ([99dd5e9](https://github.com/GauranshMathur/codex-headless-skill/commit/99dd5e9465bd61f663f6dcaa2df69032d0762d0f))
* **runner:** assemble the codex exec command line ([d8e4328](https://github.com/GauranshMathur/codex-headless-skill/commit/d8e4328f95f88ee0b2f95d039eb348dc292a291e))
* **runner:** default reasoning effort to high ([eb4bf85](https://github.com/GauranshMathur/codex-headless-skill/commit/eb4bf85989736b0f79adec044b5e61e01a27060a))
* **runner:** enforce wall-clock and idle timeouts, killing the process group ([7462750](https://github.com/GauranshMathur/codex-headless-skill/commit/746275036d61bada60e617b6649ba4ce0772c798))
* **runner:** execute runs and report a parseable summary ([f4874fb](https://github.com/GauranshMathur/codex-headless-skill/commit/f4874fb1850a7da34ff09ab8bd8f585c1785f6a6))
* **runner:** flag a clean exit with no completed turn as a failure ([f0f2691](https://github.com/GauranshMathur/codex-headless-skill/commit/f0f26916522b201e61e3997aea36d43f418cb77a))
* **runner:** let an explicit slug override the catalog pick ([7cbe08c](https://github.com/GauranshMathur/codex-headless-skill/commit/7cbe08ce0da4d2fede14537883723513745ecb40))
* **runner:** reject unknown model slugs instead of passing them through ([f9ed36c](https://github.com/GauranshMathur/codex-headless-skill/commit/f9ed36c01d303a789c5e441d11eddb304e8115fc))
* **runner:** render file changes and command results ([9d154c3](https://github.com/GauranshMathur/codex-headless-skill/commit/9d154c3c7bf03f946cfd75fc41bdcb3c5569cbaa))
* **runner:** render running commands as progress lines ([04135d8](https://github.com/GauranshMathur/codex-headless-skill/commit/04135d89c2de997cf581a741fa28c018a07d2beb))
* **runner:** require a completed turn before calling a run successful ([7247ced](https://github.com/GauranshMathur/codex-headless-skill/commit/7247ced1d158c546b1fbb21446f0d0429748b665))
* **runner:** resolve model from catalog by priority ([e77afbc](https://github.com/GauranshMathur/codex-headless-skill/commit/e77afbcf31b9b038238c841111a4227442c00f26))
* **runner:** step effort down when a model lacks the requested rung ([58b5b9a](https://github.com/GauranshMathur/codex-headless-skill/commit/58b5b9ab29530e09e3e6f231f7e98375c02c5c13))
* **runner:** stream codex JSONL live and capture the raw run ([482916a](https://github.com/GauranshMathur/codex-headless-skill/commit/482916af58aec5504f03dc8fbf166a9218b9ba87))
* **runner:** support CODEX_HEADLESS_MODEL with flag taking precedence ([d16f48c](https://github.com/GauranshMathur/codex-headless-skill/commit/d16f48c7c14ac438165b955c5b3233e64b759258))
* **runner:** treat turn.failed as fatal but tolerate transient errors ([be39032](https://github.com/GauranshMathur/codex-headless-skill/commit/be39032005ebd327394c14d696081b6185034f57))


### Bug Fixes

* **runner:** disable MCP servers by name rather than with an empty table ([db0a50c](https://github.com/GauranshMathur/codex-headless-skill/commit/db0a50c8bc949dd03f1f86099103508267a16283))
