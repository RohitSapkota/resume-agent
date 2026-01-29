#!/usr/bin/env python
from pydantic import BaseModel

from crewai.flow import Flow, listen, start, router
from crewai import LLM

from resume_agent_crewai.crews.resume_crew.resume_crew import ResumeCrew

class ResumeState(BaseModel):
    user_input: str = ""
    resume: str = ""

class ResumeFlow(Flow[ResumeState]):
    
    @start()
    def start_conversation(self):
        print("Generating sentence count")
        self.state.user_input = input("\033[1;31m What to you want to add in your resume?\033[0m  \n>> \n")
        print(f"Input received: \"{self.state.user_input}\"")

    @router(start_conversation)
    def analyze_resume(self):
        print("Analysing resume")

    @listen(analyze_resume)
    def save_resume(self):
        print("Saving resume")
        with open("resume.txt", "w") as f:
            f.write(self.state.resume)


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
