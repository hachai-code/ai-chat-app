# Claude Code Guidelines

When writing, reviewing, or refactoring code, always apply the `andrej-karpathy-skills:karpathy-guidelines` skill.

Before coding against any third-party library used in this project (Anthropic SDK, FastAPI, Pydantic, etc.), fetch the current official documentation with WebFetch and check it for: latest model IDs / version-specific APIs, deprecated parameters, recommended patterns. Do not rely on training-data knowledge for these libraries — verify first.

Do not overengineer. Prefer the simplest solution that solves the problem at hand. No speculative abstractions, no premature configurability, no features beyond what was asked. If a wrapper, helper, or layer doesn't earn its keep right now, don't add it.

Write code so someone (including the same person months later) can read it once and understand it. Use clear names over clever ones, predictable control flow, and small functions that do one thing. Avoid implicit magic, deeply nested ternaries, single-letter variables, and "you have to know X to read this" patterns.
