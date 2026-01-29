from crewai import LLM
from typing import List
import os

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

gemini_api_key = os.getenv("GEMINI_API_KEY")

@CrewBase
class ResumeCrew:
    """Resume Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def hiring_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["hiring_manager"],
            llm=LLM(model="gemini/gemini-3-flash-preview", api_key=gemini_api_key),
        )

    @task
    def read_resume(self) -> Task:
        return Task(
            config=self.tasks_config["read_resume"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Research Crew"""

        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
