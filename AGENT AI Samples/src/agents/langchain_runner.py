from src.agents.shared import run_bounded_loop
from src.models import AgentResult, HealthReport


def run(report: HealthReport) -> AgentResult:
    """Run retrieval retries and a tool-using LangChain relevance-review agent."""
    return run_bounded_loop(report, "langchain")
