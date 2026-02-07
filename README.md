# Resume Agent (crewAI)

`resume_agent_crewai` is a multi-agent workflow that improves a resume PDF and can generate a portfolio-style static website from that resume.

It is built with [crewAI](https://crewai.com), uses Gemini + OpenAI models, and is designed to preserve factual accuracy (no invented experience, skills, or metrics).

## What This Project Does

You can run one of two paths:

- `update_resume`
  - Reads `src/resume_agent_crewai/Resume.pdf`
  - Reviews it for AI/software hiring quality and ATS readiness
  - Produces:
    - updated PDF: `src/resume_agent_crewai/resume_updated.pdf`
    - review artifacts: `src/resume_agent_crewai/artifacts/review.json`

- `create_website`
  - Runs the full resume update pipeline first
  - Uses the reviewed resume text to generate a static site
  - Produces:
    - `docs/index.html`
    - `docs/styles.css`
    - `docs/script.js`
    - metadata: `docs/build_meta.json`

## How It Works

The flow is defined in `src/resume_agent_crewai/main.py`.

Resume pipeline:
1. Fingerprint source resume + request (for caching)
2. Read resume PDF via tool
3. Review content quality and hiring signal
4. Revise text and write updated PDF
5. Save feedback + build metadata

Website pipeline:
1. Build content outline from reviewed resume text
2. Generate semantic, responsive HTML/CSS/JS
3. Validate output and write files to `docs/`

Guardrails:
- Factual integrity checks (no invented resume facts)
- Output schema checks for JSON/tool responses
- Content overlap check before publishing generated website content

## Tech Stack

- Python `>=3.10,<3.14`
- `crewai[google-genai,tools]==1.9.3`
- `pypdf`
- UV for dependency management

## Quick Start

1. Install dependencies:

```bash
uv sync
```

2. Add API keys in `.env`:

```env
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

3. Run interactive flow:

```bash
uv run crewai run
```

You will be prompted to choose `update_resume` or `create_website`.

## Triggered Runs (No Prompts)

Run with JSON payload:

```bash
uv run run_with_trigger '{"user_path":"create_website","user_request":"include my latest certification if present"}'
```

Other example:

```bash
uv run run_with_trigger '{"user_path":"update_resume","user_request":"tighten bullet points for impact"}'
```

## Repository Layout

- `src/resume_agent_crewai/main.py`: Flow routing, validation, caching, artifact writing
- `src/resume_agent_crewai/crews/resume_crew/`: Resume agents + tasks
- `src/resume_agent_crewai/crews/website_crew/`: Website agents + tasks
- `src/resume_agent_crewai/tools/pdf_tool.py`: Resume PDF read/write tools
- `src/resume_agent_crewai/artifacts/`: Review + build metadata artifacts
- `docs/`: Generated static website files (GitHub Pages-friendly)

## Customization

- Agent behavior: `src/resume_agent_crewai/crews/*/config/agents.yaml`
- Task prompts/outputs: `src/resume_agent_crewai/crews/*/config/tasks.yaml`
- Model selection: `src/resume_agent_crewai/crews/*/*_crew.py`

## Notes

- Source resume must exist at `src/resume_agent_crewai/Resume.pdf` (or adjust path in `main.py`).
- The project is optimized for factual rewriting and clean static output, not for adding missing resume content automatically.
