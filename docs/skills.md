# AI Agent Skills

`fastapi-otel-common` is designed to be "AI-First". We provide pre-configured skills and instructions to help AI agents like GitHub Copilot and Antigravity understand the library's patterns and best practices.

## What are AI Agent Skills?

AI Agent Skills are specialized instruction sets and tools that can be loaded into an AI assistant's context. They allow the agent to:
- Understand library-specific patterns (e.g., how to initialize OpenTelemetry).
- Use the correct logging framework (`loguru` instead of `logging`).
- Implement security best practices by default.
- Access documentation and examples tailored to the project.

## Support for Major IDEs

### Google Antigravity
Antigravity utilizes the `.agent/skills/` directory. We provide a `fastapi-otel-common` skill that includes:
- **SKILL.md**: A comprehensive guide for the agent on how to use the library.
- **Contextual Knowledge**: Guidance on OpenTelemetry, OIDC, and Middleware implementation.

### GitHub Copilot
GitHub Copilot uses the `.github/copilot-instructions.md` file to set global project rules. Our configuration ensures Copilot:
- Prefers `create_app` over standard FastAPI initialization.
- Uses `loguru` for all logging suggestions.
- Implements asynchronous patterns correctly.

## How to Add Skills to Your Project

If you are using `fastapi-otel-common` in your own project, you can easily pull in these AI enhancements.

### Using the Skills CLI
The easiest way to add these skills is via the [skills.sh](https://skills.sh) ecosystem:

```bash
npx skills add devdenvino/fastapi_otel_common
```

This command will:
1. Initialize the `.agent/skills` folder.
2. Download the `fastapi-otel-common` skill definiton.
3. Create/Update `.github/copilot-instructions.md` with relevant rules.

### Manual Setup
Alternatively, you can manually copy the following files from the `fastapi-otel-common` repository to your project:
- `.agent/skills/fastapi-otel-common/SKILL.md`
- `.github/copilot-instructions.md`

## Benefits
- **Faster Onboarding**: AI agents can explain the codebase to new developers instantly.
- **Improved Code Quality**: Agents generate code that follows the library's patterns perfectly.
- **Zero Configuration**: Health checks and telemetry are implemented correctly by the agent without you needing to remember the syntax.
