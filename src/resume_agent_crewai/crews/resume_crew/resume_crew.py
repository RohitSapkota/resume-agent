import os
from typing import List

from crewai import LLM
from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from resume_agent_crewai.tools import ReadResumePdfTool, WriteResumePdfTool

gemini_api_key = os.getenv("GEMINI_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")


@CrewBase
class ResumeCrew:
    """Resume reader/writer and analysis crew."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def resume_reader_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_reader_writer"],
            tools=[ReadResumePdfTool()],
            llm=LLM(model="gemini/gemini-3-flash-preview", api_key=gemini_api_key),
        )

    @agent
    def resume_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_reviewer"],
            llm=LLM(model="openai/gpt-5-mini", api_key=openai_api_key),
        )

    @agent
    def hiring_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["hiring_manager"],
            tools=[WriteResumePdfTool()],
            llm=LLM(model="openai/gpt-5-mini", api_key=openai_api_key),
        )

    @task
    def read_resume_pdf(self) -> Task:
        return Task(
            config=self.tasks_config["read_resume_pdf"],  # type: ignore[index]
        )

    @task
    def review_resume(self) -> Task:
        return Task(
            config=self.tasks_config["review_resume"],  # type: ignore[index]
        )

    @task
    def finalize_resume_and_write_pdf(self) -> Task:
        return Task(
            config=self.tasks_config["finalize_resume_and_write_pdf"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Resume Crew."""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
