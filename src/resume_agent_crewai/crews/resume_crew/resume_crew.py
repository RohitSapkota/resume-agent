from crewai import LLM
from typing import List
import os

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

gemini_api_key = os.getenv("GEMINI_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")


@CrewBase
class ResumeCrew:
    """Resume Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def resume_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_analyst"],
            llm=LLM(model="gemini/gemini-3-flash-preview", api_key=gemini_api_key),
        )

    @agent
    def impact_editor(self) -> Agent:
        return Agent(
            config=self.agents_config["impact_editor"],
            llm=LLM(model="gemini/gemini-3-flash-preview", api_key=gemini_api_key),
        )

    @agent
    def ats_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["ats_reviewer"],
            llm=LLM(model="gemini/gemini-3-flash-preview", api_key=gemini_api_key),
        )

    @agent
    def hiring_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["hiring_manager"],
            llm=LLM(model="openai/gpt-5-mini", api_key=openai_api_key),
        )

    @task
    def analyze_structure(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_structure"],  # type: ignore[index]
        )

    @task
    def rewrite_for_impact(self) -> Task:
        return Task(
            config=self.tasks_config["rewrite_for_impact"],  # type: ignore[index]
        )

    @task
    def check_ats_alignment(self) -> Task:
        return Task(
            config=self.tasks_config["check_ats_alignment"],  # type: ignore[index]
        )

    @task
    def read_resume(self) -> Task:
        return Task(
            config=self.tasks_config["read_resume"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Resume Crew"""

        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
