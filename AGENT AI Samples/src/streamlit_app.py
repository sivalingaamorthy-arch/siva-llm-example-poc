from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SAMPLE_DATA_ROOT
from src.errors import PocError
from src.loader import load_report
from src.runner import run

REPORTS = {
    "R1 — Happy path": "report1_happy_path.json",
    "R2 — Safety trap": "report2_safety_trap.json",
    "R3 — Content gap (postpartum)": "report3_content_gap.json",
}
FRAMEWORKS = {
    "LangGraph — explicit workflow graph": "langgraph",
    "LangChain — tool-using validator agent": "langchain",
    "Agno — tool-using validator agent": "agno",
}

st.set_page_config(page_title="POC2 Agent Framework Comparison", page_icon="🤖", layout="wide")
st.title("Well-being Recommender — Agent framework comparison")
st.caption(
    "Synthetic learning demo only. Each framework uses the same data, OpenAI models, "
    "retrieval, safety rules, and retry limit. Not medical advice."
)

left, right = st.columns(2)
with left:
    selected_framework = st.selectbox("Agent implementation", list(FRAMEWORKS))
with right:
    selected_report = st.selectbox("Synthetic report", list(REPORTS))

report_path = SAMPLE_DATA_ROOT / "reports" / REPORTS[selected_report]
report = load_report(report_path)
with st.expander(f"Inspect input report {report.report_id}"):
    st.json(report.model_dump(mode="json"))

st.warning(
    "Report notes and retrieved article text are sent to OpenAI. Use only these "
    "bundled synthetic reports; never use real health data."
)
if st.button("Run agent", type="primary"):
    try:
        with st.spinner("Agent is retrieving and validating recommendations…"):
            result = run(report, FRAMEWORKS[selected_framework])
        st.session_state["agent_result"] = result.model_dump(mode="json")
        st.success(
            f"Run complete. Retries: {result.retry_count}; "
            f"fallback: {'yes' if result.used_fallback else 'no'}."
        )
    except PocError as exc:
        st.error(str(exc))

payload = st.session_state.get("agent_result")
if payload and payload["report_id"] == report.report_id and payload["framework"] == FRAMEWORKS[selected_framework]:
    st.subheader("Run summary")
    st.write(
        f"**Markers:** {', '.join(payload['markers']) or 'none'}  \n"
        f"**Unmatched topics:** {', '.join(payload['unmatched_topics']) or 'none'}  \n"
        f"**Framework:** {payload['framework']} · **Retries:** {payload['retry_count']} · "
        f"**Fallback:** {'Yes' if payload['used_fallback'] else 'No'}"
    )
    if payload["used_fallback"]:
        st.warning("Generic fallback returned. These defaults do not necessarily address the report.")
    for key, title in (("physical", "Physical recommendations"), ("mental", "Mental recommendations")):
        st.subheader(title)
        for candidate in payload[key]:
            article = candidate["article"]
            st.markdown(
                f"**{article['title']}** (`{article['id']}`) · "
                f"Similarity `{candidate['similarity']:.4f}` · "
                f"Intensity `{article['intensity']}` · Source `{article['source']}`"
            )
            with st.expander(f"Article text — {article['id']}"):
                st.write(article["body"])
    st.subheader("Summary")
    st.markdown(payload["summary"])
    st.subheader("Agent trace")
    st.dataframe(payload["trace"], use_container_width=True, hide_index=True)
    st.caption(
        f"Models: {payload['generation_model']} / {payload['embedding_model']}. "
        "JSON trace is saved under output/runs/."
    )
