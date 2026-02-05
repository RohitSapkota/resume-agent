from crewai import LLM
from typing import List
import os

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

gemini_api_key = os.getenv("GEMINI_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")


@CrewBase
class WebsiteCrew:
    """Website Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def content_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["content_strategist"],
            llm=LLM(model="gemini/gemini-3-flash-preview", api_key=gemini_api_key),
        )

    @agent
    def visual_designer(self) -> Agent:
        return Agent(
            config=self.agents_config["visual_designer"],
            llm=LLM(model="openai/gpt-5-mini", api_key=openai_api_key),
        )

    @agent
    def accessibility_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["accessibility_reviewer"],
            llm=LLM(model="gemini/gemini-3-flash-preview", api_key=gemini_api_key),
        )

    @agent
    def website_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["website_engineer"],
            llm=LLM(model="openai/gpt-5-mini", api_key=openai_api_key),
        )

    @task
    def craft_content_outline(self) -> Task:
        return Task(
            config=self.tasks_config["craft_content_outline"],  # type: ignore[index]
        )

    @task
    def define_visual_direction(self) -> Task:
        return Task(
            config=self.tasks_config["define_visual_direction"],  # type: ignore[index]
        )

    @task
    def audit_accessibility(self) -> Task:
        return Task(
            config=self.tasks_config["audit_accessibility"],  # type: ignore[index]
        )

    @task
    def generate_resume_site(self) -> Task:
        return Task(
            config=self.tasks_config["generate_resume_site"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Website Crew"""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
