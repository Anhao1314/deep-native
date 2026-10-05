# Upstream references

Documentation checked on 2026-10-06. Upstream behavior can change; the local tests do
not certify every future Claude Code version.

- [Claude Code Skills](https://code.claude.com/docs/en/skills): project Skill location,
  slash invocation, supporting files and skill-directory/session substitutions.
- [Claude Code Hooks](https://code.claude.com/docs/en/hooks): SessionStart/Stop events,
  JSON context output, stop decisions and stop_hook_active loop handling.
- [DeepSeek Anthropic API compatibility](https://api-docs.deepseek.com/guides/anthropic_api/):
  official compatible endpoint and field-support differences. Not every Anthropic
  API field is implemented, and some are ignored.
- [DeepSeek Claude Code integration](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code/):
  linked by the compatibility page. This exact page timed out during authoring, so
  this release does not rely on copied tuning values from it.

This implementation uses documented interfaces and original project instructions/code;
it does not copy Claude's private system prompt. API compatibility does not establish
behavioral or capability equivalence. Provider pricing/model aliases are not hardcoded.
