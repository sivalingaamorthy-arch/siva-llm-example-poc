from src.errors import PocError
from src.models import AgentResult, HealthReport


def run(report: HealthReport, framework: str) -> AgentResult:
    if framework == "langgraph":
        from src.agents.langgraph_agent import run_langgraph

        return run_langgraph(report)
    if framework == "langchain":
        from src.agents.langchain_runner import run as run_langchain

        return run_langchain(report)
    if framework == "agno":
        from src.agents.agno_runner import run as run_agno

        return run_agno(report)
    raise PocError(f"Unknown framework {framework!r}. Choose langchain, langgraph, or agno.")
