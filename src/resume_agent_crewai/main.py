#!/usr/bin/env python
import json
import os
import re
from pypdf import PdfReader

from pydantic import BaseModel

from crewai import LLM
from crewai.flow import Flow, listen, start, router

from resume_agent_crewai.crews.resume_crew.resume_crew import ResumeCrew
from resume_agent_crewai.crews.website_crew.website_crew import WebsiteCrew

class ResumeState(BaseModel):
    user_action: str = ""
    user_input: str = ""
    resume: str = ""
    review: str = ""
    site_output_dir: str = "docs"


class ResumeFlow(Flow[ResumeState]):
    @staticmethod
    def _normalize_text(text: str) -> str:
        # Reduce token usage without changing content semantics
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _extract_visible_text_from_html(html: str) -> str:
        # Remove scripts/styles and HTML tags to approximate visible content
        html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
        html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
        html = re.sub(r"(?s)<[^>]+>", " ", html)
        html = re.sub(r"[ \t]+", " ", html)
        html = re.sub(r"\n{2,}", "\n", html)
        return html.strip()

    @staticmethod
    def _content_overlap_ratio(source_text: str, generated_text: str) -> float:
        def _tokens(s: str) -> list[str]:
            return re.findall(r"[a-z0-9]+", s.lower())

        src = set(_tokens(source_text))
        gen = _tokens(generated_text)
        if not gen:
            return 0.0
        overlap = sum(1 for t in gen if t in src)
        return overlap / max(len(gen), 1)

    @start()
    def start_conversation(self):
        self.state.user_action = input(
            "\033[1;31m What would you like to do? (e.g., update my resume or give a website)\033[0m  \n>> \n"
        )
        print(f"Action received: \"{self.state.user_action}\"")

    @router(start_conversation)
    def analyze_resume(self):
        prompt = (
            "Classify the user's request into exactly one label:\n"
            "- RESUME_UPDATE: update/edit/add to resume content\n"
            "- RESUME_SITE: generate a resume website or site\n"
            "- UNSUPPORTED: anything else\n\n"
            "Examples:\n"
            "User request: \"Update my resume with my new role at Acme\"\n"
            "Label: RESUME_UPDATE\n"
            "User request: \"Add my latest project to my resume\"\n"
            "Label: RESUME_UPDATE\n"
            "User request: \"Create a personal website from my resume\"\n"
            "Label: RESUME_SITE\n"
            "User request: \"Build a resume site and host it on GitHub\"\n"
            "Label: RESUME_SITE\n"
            "User request: \"What is the weather today?\"\n"
            "Label: UNSUPPORTED\n"
            "User request: \"Send me interview tips\"\n"
            "Label: UNSUPPORTED\n\n"
            f"User request: \"{self.state.user_action}\"\n\n"
            "Return only one label from the list."
        )

        llm = LLM(model="gemini/gemini-3-flash-preview", api_key=os.getenv("GEMINI_API_KEY"))
        decision = llm.call(messages=prompt).strip().upper()

        label_map = {
            "RESUME_UPDATE": "collect_update",
            "RESUME_SITE": "render_resume_site",
            "UNSUPPORTED": "unsupported_action",
        }
        if decision in label_map:
            return label_map[decision]

        # Fallback if the model returns something unexpected
        return "UNSUPPORTED"

    @listen("collect_update")
    def collect_update(self):
        print("Reading existing resume...")
        reader = PdfReader("src/resume_agent_crewai/Resume.pdf")
        for page in reader.pages:
            resume = page.extract_text()
            self.state.resume += resume + "\n"
        self.state.resume = self._normalize_text(self.state.resume)
        self.state.user_input = input(
            "\033[1;31m What do you want to add to your resume?\033[0m  \n>> \n"
        )
        print(f"Input received: \"{self.state.user_input}\"")

        print("Analyzing resume...")
        hiring_manager = ResumeCrew()
        result = hiring_manager.crew().kickoff(
            {
                "resume_text": self.state.resume,
                "user_input": self.state.user_input,
            }
        )
        def _parse_feedback_json(raw: str) -> list[dict]:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as e:
                raise Exception(f"Resume crew output was not valid JSON: {e}")

            if not isinstance(payload, list):
                raise Exception("Resume crew output must be a JSON array.")

            required_keys = {"category", "severity", "issue", "recommendation"}
            for i, item in enumerate(payload):
                if not isinstance(item, dict):
                    raise Exception(f"Resume crew item {i} is not an object.")
                missing = required_keys - set(item.keys())
                if missing:
                    raise Exception(f"Resume crew item {i} missing keys: {sorted(missing)}")
            return payload

        feedback_items = _parse_feedback_json(result.raw)
        self.state.review = json.dumps(feedback_items, indent=2)

    @listen("unsupported_action")
    def unsupported_action(self):
        print("Unsupported action for now. Please try: update resume or generate website.")

    @listen("render_resume_site")
    def render_resume_site(self):
        print("Reading existing resume...")
        reader = PdfReader("src/resume_agent_crewai/Resume.pdf")
        for page in reader.pages:
            resume = page.extract_text()
            self.state.resume += resume + "\n"
        self.state.resume = self._normalize_text(self.state.resume)
        if not self._is_reasonable_resume_text(self.state.resume):
            raise Exception(
                "Resume text extraction looks empty or garbled. "
                "Please check Resume.pdf or provide a text-based PDF."
            )

        website_crew = WebsiteCrew()
        result = website_crew.crew().kickoff({"resume_text": self.state.resume})

        def _extract_json(raw: str) -> dict:
            raw = raw.strip()
            # Try direct parse first
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass

            # Strip fenced code blocks if present
            fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if fence_match:
                try:
                    return json.loads(fence_match.group(1))
                except json.JSONDecodeError:
                    pass

            # Fallback: extract the first JSON object in the text
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    pass

            raise Exception("Website crew output was not valid JSON.")

        payload = _extract_json(result.raw)

        html_doc = payload.get("html", "")
        css = payload.get("css", "")
        js = payload.get("js", "")

        if not html_doc or not css or not js:
            raise Exception("Website crew output missing HTML, CSS, or JS fields.")

        visible = self._extract_visible_text_from_html(html_doc)
        overlap = self._content_overlap_ratio(self.state.resume, visible)
        if overlap < 0.7:
            raise Exception(
                "Generated HTML appears to include substantial content not found in the resume. "
                "Please ensure the resume text is correct and try again."
            )

        output_dir = self.state.site_output_dir
        os.makedirs(output_dir, exist_ok=True)
        index_path = os.path.join(output_dir, "index.html")
        css_path = os.path.join(output_dir, "styles.css")
        js_path = os.path.join(output_dir, "script.js")

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html_doc)
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(css)
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(js)

        print(f"Website generated in {output_dir}/index.html")

    @listen("collect_update")
    def save_resume(self):
        print("Saving resume.")
        with open("src/resume_agent_crewai/feedback.txt", "w") as f:
            f.write(self.state.review)

    @staticmethod
    def _is_reasonable_resume_text(text: str) -> bool:
        if len(text) < 200:
            return False
        letters = sum(ch.isalpha() for ch in text)
        if letters == 0:
            return False
        return letters / max(len(text), 1) > 0.4

def kickoff():
    resume_flow = ResumeFlow(tracing=True)
    resume_flow.kickoff()


def plot():
    resume_flow = ResumeFlow()
    resume_flow.plot()


def run_with_trigger():
    """
    Run the flow with trigger payload.
    """
    import json
    import sys

    # Get trigger payload from command line argument
    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    # Create flow and kickoff with trigger payload
    # The @start() methods will automatically receive crewai_trigger_payload parameter
    resume_flow = ResumeFlow()

    try:
        result = resume_flow.kickoff({"crewai_trigger_payload": trigger_payload})
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the flow with trigger: {e}")


if __name__ == "__main__":
    kickoff()
