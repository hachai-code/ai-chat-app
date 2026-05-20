# Claude Code Guidelines

When writing, reviewing, or refactoring code, always apply the `andrej-karpathy-skills:karpathy-guidelines` skill.

Before coding against any third-party library used in this project (Anthropic SDK, FastAPI, Pydantic, etc.), fetch the current official documentation with WebFetch and check it for: latest model IDs / version-specific APIs, deprecated parameters, recommended patterns. Do not rely on training-data knowledge for these libraries — verify first.
