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

**Add your `GEMINI_API_KEY` and `OPENAI_API_KEY` into the `.env` file**

Example `.env`:
```env
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

## Running the Project

To kickstart your flow and begin execution, run this from the root folder of your project:

```bash
crewai run
```

This command initializes the `resume_agent_crewai` Flow as defined in your configuration.

## Outputs

Depending on your flow configuration, you should expect:
- Resume Crew: finalized factual resume text, prioritized feedback, and a new updated PDF at `src/resume_agent_crewai/resume_updated.pdf`
- Website Crew: `index.html`, `styles.css`, `script.js`, and `build_meta.json` written to `docs/`

## Crews Overview

The project includes two crews:

- Resume Crew: A reader/writer + analysis pipeline that reads `Resume.pdf` via tool, evaluates and rewrites to a high AI-engineer standard, preserves factual content, and writes an updated PDF.
- Website Crew: A pipeline that transforms reviewed resume content into a static GitHub Pages-friendly site.

## New Core Flow

1. User selects one path: `update_resume` or `create_website`.
2. `update_resume`: runs only the Resume Crew and outputs `resume_updated.pdf`.
3. `create_website`: runs Resume Crew first, then Website Crew using the reviewed resume text.
4. User-requested additions (for example, new experience or certifications) are incorporated without inventing facts.

Task coordination supports parallel execution where configured (`async_execution: true`) and uses `context` for dependent handoffs. In the new resume-first flow, resume tasks are intentionally sequential for strict factual control.

Crew configuration lives in:
- `src/resume_agent_crewai/crews/resume_crew/config/agents.yaml`
- `src/resume_agent_crewai/crews/resume_crew/config/tasks.yaml`
- `src/resume_agent_crewai/crews/website_crew/config/agents.yaml`
- `src/resume_agent_crewai/crews/website_crew/config/tasks.yaml`

## How Task Coordination Works

Independent tasks run in parallel only where `async_execution: true` is configured. Dependent tasks receive upstream outputs via `context`, and sequential execution is used where strict ordering is required.

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

Trigger-based run example:
```bash
run_with_trigger '{"user_request":"create a resume website and include my latest certification"}'
```

If you want to execute only one crew, update the flow entrypoint in:
- `src/resume_agent_crewai/main.py`

## Support

For support, questions, or feedback regarding crewAI:
- Visit the [documentation](https://docs.crewai.com)
- Reach out via the [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join the Discord](https://discord.com/invite/X4JWnZnxPb)
