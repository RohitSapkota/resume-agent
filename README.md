# Resume Agent (crewAI)

This project orchestrates multi-agent crews to:
- critique and improve resumes
- generate a polished static resume website (HTML/CSS/JS)

It is powered by [crewAI](https://crewai.com) and configured for parallel task execution where possible, with explicit data handoff between dependent tasks.

## Installation

Ensure you have Python >=3.10 <3.14 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling.

First, if you haven't already, install uv from the official site:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Next, navigate to your project directory and install the dependencies:

(Optional) Lock the dependencies and install them by using the CLI command:
```bash
crewai install
```

### Configuration

**Add your `GEMINI_API_KEY` into the `.env` file**

Example `.env`:
```env
GEMINI_API_KEY=your_key_here
```

## Running the Project

To kickstart your flow and begin execution, run this from the root folder of your project:

```bash
crewai run
```

This command initializes the `resume_agent_crewai` Flow as defined in your configuration.

## Outputs

Depending on your flow configuration, you should expect:
- Resume Crew: JSON feedback items (prioritized, actionable)
- Website Crew: JSON with `title`, `html`, `css`, `js` fields

## Crews Overview

The project includes two crews:

- Resume Crew: A multi-agent pipeline that analyzes structure, rewrites for impact, checks ATS alignment, and synthesizes prioritized feedback.
- Website Crew: A multi-agent pipeline that defines content structure, visual direction, accessibility guidance, and generates the final HTML/CSS/JS.

Task execution is optimized so independent tasks run in parallel (`async_execution: true`) while dependent tasks receive upstream outputs via `context`. This keeps sequential execution a necessity only when required by data dependencies.

Crew configuration lives in:
- `src/resume_agent_crewai/crews/resume_crew/config/agents.yaml`
- `src/resume_agent_crewai/crews/resume_crew/config/tasks.yaml`
- `src/resume_agent_crewai/crews/website_crew/config/agents.yaml`
- `src/resume_agent_crewai/crews/website_crew/config/tasks.yaml`

## How Task Coordination Works

Independent tasks run in parallel using `async_execution: true`. Dependent tasks receive upstream outputs via `context`. This makes sequential execution a necessity only when required by data dependencies.

## Common Changes

If you want to customize behavior:
- Update agent roles and goals in `config/agents.yaml`.
- Update task prompts, expectations, or dependencies in `config/tasks.yaml`.
- Change model or provider in `crews/*/*_crew.py`.

## Example Usage

Run the flow:
```bash
crewai run
```

If you want to execute only one crew, update the flow entrypoint in:
- `src/resume_agent_crewai/main.py`

## Support

For support, questions, or feedback regarding crewAI:
- Visit the [documentation](https://docs.crewai.com)
- Reach out via the [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join the Discord](https://discord.com/invite/X4JWnZnxPb)
