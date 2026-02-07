#!/usr/bin/env python
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, Field

from crewai.flow import Flow, listen, router, start

from resume_agent_crewai.crews.resume_crew.resume_crew import ResumeCrew
from resume_agent_crewai.crews.website_crew.website_crew import WebsiteCrew


class ResumePackage(BaseModel):
    source_pdf_path: str = "src/resume_agent_crewai/Resume.pdf"
    source_pdf_hash: str = ""
    flow_version: str = ""
    cache_key: str = ""
    cache_hit: bool = False
    final_resume_text: str = ""
    updated_pdf_path: str = ""
    feedback_items: list[dict[str, Any]] = Field(default_factory=list)
    applied_user_updates: list[str] = Field(default_factory=list)
    skipped_user_updates: list[str] = Field(default_factory=list)


class ResumeState(BaseModel):
    user_path: str = ""
    user_request: str = ""
    site_output_dir: str = "docs"
    artifacts_dir: str = "src/resume_agent_crewai/artifacts"
    package: ResumePackage = Field(default_factory=ResumePackage)


class ResumeFlow(Flow[ResumeState]):
    UPDATE_RESUME = "update_resume"
    CREATE_WEBSITE = "create_website"
    RESUME_PIPELINE = "resume_pipeline"
    FLOW_VERSION = "resume-flow-v2"
    CACHE_DIR = Path("src/resume_agent_crewai/.cache/resume_pipeline")
    FEEDBACK_TXT_PATH = Path("src/resume_agent_crewai/feedback.txt")
    REVIEW_JSON_NAME = "review.json"
    BUILD_META_NAME = "build_meta.json"

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _extract_visible_text_from_html(html: str) -> str:
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

    @staticmethod
    def _classify_path(text: str) -> str | None:
        raw = text.strip().lower()
        if not raw:
            return None

        token = re.sub(r"[^a-z_]", "", raw)
        if token in {"update_resume", "updateresume"}:
            return ResumeFlow.UPDATE_RESUME
        if token in {"create_website", "createwebsite"}:
            return ResumeFlow.CREATE_WEBSITE

        if any(
            keyword in raw
            for keyword in (
                "create website",
                "build website",
                "portfolio website",
                "portfolio site",
                "resume website",
                "website",
            )
        ):
            return ResumeFlow.CREATE_WEBSITE
        if any(
            keyword in raw
            for keyword in (
                "update resume",
                "edit resume",
                "improve resume",
                "resume update",
                "resume",
                "cv",
            )
        ):
            return ResumeFlow.UPDATE_RESUME
        return None

    @staticmethod
    def _extract_json_object(raw: str, source_name: str) -> dict[str, Any]:
        raw = raw.strip()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fence_match:
            parsed = json.loads(fence_match.group(1))
            if isinstance(parsed, dict):
                return parsed

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, dict):
                return parsed

        raise Exception(f"{source_name} output was not valid JSON object.")

    @staticmethod
    def _is_reasonable_resume_text(text: str) -> bool:
        if len(text) < 200:
            return False
        letters = sum(ch.isalpha() for ch in text)
        if letters == 0:
            return False
        return letters / max(len(text), 1) > 0.4

    @staticmethod
    def _is_valid_website_payload(payload: dict[str, Any]) -> tuple[bool, str]:
        required_str_keys = ("title", "html", "css", "js")
        for key in required_str_keys:
            value = payload.get(key)
            if not isinstance(value, str) or not value.strip():
                return False, f"Website crew output missing/invalid `{key}`."

        html_doc = payload["html"].lower()
        if "styles.css" not in html_doc:
            return False, "Generated HTML must reference `styles.css`."
        if "script.js" not in html_doc:
            return False, "Generated HTML must reference `script.js`."
        return True, ""

    @staticmethod
    def _read_sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _stage_extract_resume_fingerprint(self) -> None:
        source_path = Path(self.state.package.source_pdf_path).expanduser().resolve()
        if not source_path.exists():
            raise Exception(f"Source resume PDF not found: {source_path}")

        source_hash = self._read_sha256(source_path)
        normalized_request = self._normalize_text(self.state.user_request)
        signature = "|".join((self.FLOW_VERSION, source_hash, normalized_request))
        cache_key = hashlib.sha256(signature.encode("utf-8")).hexdigest()

        self.state.package.source_pdf_path = str(source_path)
        self.state.package.source_pdf_hash = source_hash
        self.state.package.flow_version = self.FLOW_VERSION
        self.state.package.cache_key = cache_key

    def _cache_file_path(self) -> Path:
        if not self.state.package.cache_key:
            raise Exception("Cache key not set before cache path resolution.")
        return self.CACHE_DIR / f"{self.state.package.cache_key}.json"

    def _set_resume_outputs(
        self,
        *,
        final_resume_text: str,
        updated_pdf_path: str,
        feedback_items: list[dict[str, Any]],
        applied_user_updates: list[str],
        skipped_user_updates: list[str],
        cache_hit: bool,
    ) -> None:
        normalized_resume = self._normalize_text(final_resume_text)
        if not self._is_reasonable_resume_text(normalized_resume):
            raise Exception(
                "Resume pipeline produced empty or low-quality resume text. "
                "Please verify Resume.pdf is text-based and rerun."
            )

        updated_pdf = Path(updated_pdf_path).expanduser().resolve()
        if not updated_pdf.exists():
            raise Exception(f"Updated resume PDF not found at: {updated_pdf}")

        if not isinstance(feedback_items, list) or not feedback_items:
            raise Exception("Resume pipeline output field `feedback_items` must be a non-empty array.")

        self.state.package.final_resume_text = normalized_resume
        self.state.package.updated_pdf_path = str(updated_pdf)
        self.state.package.feedback_items = feedback_items
        self.state.package.applied_user_updates = applied_user_updates
        self.state.package.skipped_user_updates = skipped_user_updates
        self.state.package.cache_hit = cache_hit

    def _write_resume_artifacts(self) -> None:
        artifacts_dir = Path(self.state.artifacts_dir).expanduser().resolve()
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        review_json_path = artifacts_dir / self.REVIEW_JSON_NAME
        review_payload = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "flow_version": self.state.package.flow_version,
            "cache_key": self.state.package.cache_key,
            "feedback_items": self.state.package.feedback_items,
            "applied_user_updates": self.state.package.applied_user_updates,
            "skipped_user_updates": self.state.package.skipped_user_updates,
        }
        with open(review_json_path, "w", encoding="utf-8") as f:
            json.dump(review_payload, f, indent=2)

        self.FEEDBACK_TXT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.FEEDBACK_TXT_PATH, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.state.package.feedback_items, indent=2))

    def _load_resume_cache(self) -> bool:
        cache_path = self._cache_file_path()
        if not cache_path.exists():
            return False

        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False

        required = {"final_resume_text", "updated_pdf_path", "feedback_items"}
        if required - set(payload.keys()):
            return False

        self._set_resume_outputs(
            final_resume_text=str(payload["final_resume_text"]),
            updated_pdf_path=str(payload["updated_pdf_path"]),
            feedback_items=payload["feedback_items"],
            applied_user_updates=[
                str(item) for item in payload.get("applied_user_updates", [])
            ],
            skipped_user_updates=[
                str(item) for item in payload.get("skipped_user_updates", [])
            ],
            cache_hit=True,
        )
        self._write_resume_artifacts()
        print(f"Resume pipeline cache hit for key: {self.state.package.cache_key}")
        return True

    def _save_resume_cache(self) -> None:
        cache_path = self._cache_file_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "flow_version": self.state.package.flow_version,
            "cache_key": self.state.package.cache_key,
            "source_pdf_path": self.state.package.source_pdf_path,
            "source_pdf_hash": self.state.package.source_pdf_hash,
            "final_resume_text": self.state.package.final_resume_text,
            "updated_pdf_path": self.state.package.updated_pdf_path,
            "feedback_items": self.state.package.feedback_items,
            "applied_user_updates": self.state.package.applied_user_updates,
            "skipped_user_updates": self.state.package.skipped_user_updates,
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def _stage_review_update_render_pdf(self) -> None:
        print("Running staged resume pipeline: review -> update -> render PDF...")
        result = ResumeCrew().crew().kickoff(
            inputs={
                "resume_pdf_path": self.state.package.source_pdf_path,
                "user_input": self.state.user_request,
                "output_pdf_path": "src/resume_agent_crewai/resume_updated.pdf",
            }
        )

        payload = self._extract_json_object(result.raw, "Resume crew")
        required_keys = {"final_resume_text", "updated_pdf_path", "feedback_items"}
        missing = required_keys - set(payload.keys())
        if missing:
            raise Exception(f"Resume crew output missing keys: {sorted(missing)}")

        self._set_resume_outputs(
            final_resume_text=str(payload["final_resume_text"]),
            updated_pdf_path=str(payload["updated_pdf_path"]),
            feedback_items=payload["feedback_items"],
            applied_user_updates=[
                str(item) for item in payload.get("applied_user_updates", [])
            ],
            skipped_user_updates=[
                str(item) for item in payload.get("skipped_user_updates", [])
            ],
            cache_hit=False,
        )
        self._write_resume_artifacts()
        self._save_resume_cache()
        print(f"Updated resume PDF generated at: {self.state.package.updated_pdf_path}")

    def _write_build_metadata(self, extra_fields: dict[str, Any] | None = None) -> str:
        artifacts_dir = Path(self.state.artifacts_dir).expanduser().resolve()
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        review_json_path = artifacts_dir / self.REVIEW_JSON_NAME
        metadata = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "flow_path": self.state.user_path,
            "flow_version": self.state.package.flow_version,
            "cache": {
                "key": self.state.package.cache_key,
                "hit": self.state.package.cache_hit,
            },
            "resume": {
                "source_pdf_path": self.state.package.source_pdf_path,
                "source_pdf_hash": self.state.package.source_pdf_hash,
                "updated_pdf_path": self.state.package.updated_pdf_path,
                "review_json_path": str(review_json_path),
            },
        }
        if extra_fields:
            metadata.update(extra_fields)

        metadata_path = artifacts_dir / self.BUILD_META_NAME
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        return str(metadata_path)

    @start()
    def start_conversation(self, crewai_trigger_payload: dict | None = None):
        trigger = crewai_trigger_payload or {}
        if not isinstance(trigger, dict):
            trigger = {}

        triggered_path = (
            str(trigger.get("user_path", "")).strip()
            or str(trigger.get("path", "")).strip()
            or str(trigger.get("action", "")).strip()
        )
        triggered_request = str(trigger.get("user_request", "")).strip() or str(
            trigger.get("user_action", "")
        ).strip()

        route_signal = triggered_path or triggered_request
        classified_path = self._classify_path(route_signal)
        if classified_path:
            self.state.user_path = classified_path
            print(f"Path received from trigger: \"{self.state.user_path}\"")
        else:
            path_input = input(
                "\033[1;31m Choose path: `update_resume` (resume only) or `create_website` (resume + website)\033[0m  \n>> \n"
            ).strip()
            classified_input_path = self._classify_path(path_input)
            if not classified_input_path:
                raise Exception(
                    "Could not classify route. Please provide a clear intent like "
                    "'update my resume' or 'create website'."
                )
            self.state.user_path = classified_input_path
            print(f"Path received: \"{self.state.user_path}\"")

        if triggered_request:
            self.state.user_request = triggered_request
            print(f"Action received from trigger: \"{self.state.user_request}\"")
        elif self.state.user_path == self.UPDATE_RESUME:
            self.state.user_request = input(
                "\033[1;31m What updates do you want for your resume? (include any new experience/certifications)\033[0m  \n>> \n"
            ).strip()
            print(f"Action received: \"{self.state.user_request}\"")
        elif self.state.user_path == self.CREATE_WEBSITE:
            self.state.user_request = input(
                "\033[1;31m Optional: any resume updates before website generation? (press Enter to skip)\033[0m  \n>> \n"
            ).strip()

    @router(start_conversation)
    def route_flow(self):
        if self.state.user_path in {self.UPDATE_RESUME, self.CREATE_WEBSITE}:
            return self.RESUME_PIPELINE
        raise Exception("Unable to route flow. Unknown path.")

    @listen(RESUME_PIPELINE)
    def run_resume_pipeline(self):
        self._stage_extract_resume_fingerprint()
        if not self._load_resume_cache():
            self._stage_review_update_render_pdf()

    @router(run_resume_pipeline)
    def route_after_resume_pipeline(self):
        if self.state.user_path == self.UPDATE_RESUME:
            return self.UPDATE_RESUME
        if self.state.user_path == self.CREATE_WEBSITE:
            return self.CREATE_WEBSITE
        raise Exception("Unable to route flow after resume pipeline. Unknown path.")

    @listen(UPDATE_RESUME)
    def update_resume_only(self):
        metadata_path = self._write_build_metadata()
        print("Resume update flow complete.")
        print(f"Build metadata generated in {metadata_path}")

    @listen(CREATE_WEBSITE)
    def create_website_with_resume_review(self):
        print("Generating website from reviewed resume content...")
        resume_text = self.state.package.final_resume_text

        website_crew = WebsiteCrew()
        result = website_crew.crew().kickoff({"resume_text": resume_text})
        payload = self._extract_json_object(result.raw, "Website crew")

        valid, reason = self._is_valid_website_payload(payload)
        if not valid:
            raise Exception(reason)

        html_doc = payload["html"]
        css = payload["css"]
        js = payload["js"]

        visible = self._extract_visible_text_from_html(html_doc)
        overlap = self._content_overlap_ratio(resume_text, visible)
        if overlap < 0.7:
            raise Exception(
                "Generated HTML includes substantial content not found in the resume. "
                "Please rerun and verify resume extraction."
            )

        output_dir = Path(self.state.site_output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        index_path = output_dir / "index.html"
        css_path = output_dir / "styles.css"
        js_path = output_dir / "script.js"

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html_doc)
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(css)
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(js)

        website_metadata = {
            "website": {
                "title": payload["title"],
                "output_dir": str(output_dir),
                "index_html": str(index_path),
                "styles_css": str(css_path),
                "script_js": str(js_path),
            },
            "site_files": {
                "index_html": str(index_path),
                "styles_css": str(css_path),
                "script_js": str(js_path),
            },
        }
        artifacts_metadata_path = self._write_build_metadata(extra_fields=website_metadata)

        docs_metadata_path = output_dir / self.BUILD_META_NAME
        with open(docs_metadata_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "flow_path": self.CREATE_WEBSITE,
                    "updated_resume_pdf": self.state.package.updated_pdf_path,
                    "site_files": website_metadata["site_files"],
                },
                f,
                indent=2,
            )

        print(f"Website generated in {index_path}")
        print(f"Website metadata generated in {docs_metadata_path}")
        print(f"Build metadata generated in {artifacts_metadata_path}")


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
    import sys

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    resume_flow = ResumeFlow()

    try:
        result = resume_flow.kickoff({"crewai_trigger_payload": trigger_payload})
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the flow with trigger: {e}")


if __name__ == "__main__":
    kickoff()
