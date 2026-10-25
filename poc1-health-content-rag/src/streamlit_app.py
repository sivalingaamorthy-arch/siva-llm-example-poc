from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.errors import PocError
from src.pipeline import load_report, run_recommendation, save_result

REPORTS = {
    "R1 — Happy path": "report1_happy_path.json",
    "R2 — Safety trap": "report2_safety_trap.json",
    "R3 — Content gap (postpartum)": "report3_content_gap.json",
}

st.set_page_config(page_title="Well-being RAG POC 1", page_icon="📚", layout="wide")
st.title("Well-being Recommender — RAG testing")
st.caption(
    "Synthetic learning demo only. Not medical advice; do not enter real health data."
)

selection = st.selectbox("Choose a bundled synthetic report", list(REPORTS))
report_path = PROJECT_ROOT / "reports" / REPORTS[selection]
report = load_report(report_path)
st.write(f"Report: **{report.report_id}**")
st.json(report.model_dump(mode="json"))

if st.button("Run recommendation", type="primary"):
    try:
        with st.spinner("Retrieving articles and generating the summary…"):
            result = run_recommendation(report)
            output_path = save_result(result)
        st.session_state["last_result"] = result.model_dump(mode="json")
        st.success(f"Run complete. Saved output to `{output_path.relative_to(output_path.parents[1])}`.")
    except PocError as exc:
        st.error(str(exc))

result_payload = st.session_state.get("last_result")
if result_payload and result_payload["report_id"] == report.report_id:
    st.subheader("Parsed markers")
    st.write(result_payload["markers"] or ["No risk markers detected"])
    st.caption(
        f"Generation: {result_payload['generation_model']} · "
        f"Embeddings: {result_payload['embedding_model']}"
    )

    for key, heading in (("physical", "Physical recommendations"), ("mental", "Mental well-being recommendations")):
        st.subheader(heading)
        recommendations = result_payload[key]
        if not recommendations:
            st.info("No eligible articles were found for this category.")
        for item in recommendations:
            article = item["article"]
            st.markdown(
                f"**{article['title']}** (`{article['id']}`)  \n"
                f"Similarity: `{item['similarity']:.4f}` · "
                f"Intensity: `{article['intensity']}` · Source: `{article['source']}`"
            )
            with st.expander("Read article snapshot"):
                st.write(article["body"])
    if report.report_id == "R3":
        st.warning(
            "Content-gap demonstration: these are the nearest eligible articles, "
            "not necessarily relevant postpartum content. Review their scores and text."
        )
    st.subheader("Grounded summary")
    st.markdown(result_payload["summary"])
