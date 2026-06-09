"""
IT Help Desk Support Agent — web frontend.

Run with:
    streamlit run src/app.py
or simply double-click start.bat (Windows) / start.command (macOS).

This file is a thin presentation layer: all the business logic lives in
agent.py and its sibling modules. The frontend only handles input, output
and the visual representation of the audit signals.
"""

import logging
import sys
from pathlib import Path

# Ensure src/ is on sys.path so the flat-import style used in the other
# modules works whether Streamlit is launched from the project root or
# from inside src/.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from agent import SupportAgent

# ---------------------------------------------------------------------------
# Logging — configure once, then silence the noisiest libraries so that the
# launcher terminal stays readable during the session.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
for _noisy in ("httpx", "huggingface_hub", "sentence_transformers", "urllib3"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Page configuration & constants
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="IT Help Desk Agent",
    layout="centered",
)

URGENCY_COLOR = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}

EXAMPLES = [
    "I can't connect to the VPN from home, I've been trying all morning and nothing works.",
    "URGENT: I clicked on a phishing link and now my screen is doing weird things.",
    "Where can I find the Wi-Fi password for the guest network?",
    "URGENTE: ho cliccato su un link sospetto, il portatile si comporta in modo strano.",
]


@st.cache_resource(show_spinner=False)
def get_agent() -> SupportAgent:
    """Build the agent once and reuse across reruns (caches model + embeddings)."""
    return SupportAgent(top_k=3)


# ---------------------------------------------------------------------------
# Session-state callbacks
# ---------------------------------------------------------------------------
def _set_query(text: str) -> None:
    """Populate the text area from an example button and clear the old result."""
    st.session_state["query"] = text
    st.session_state["result"] = None


def _clear_all() -> None:
    """Reset both the query and the displayed result."""
    st.session_state["query"] = ""
    st.session_state["result"] = None


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def _render_result(result) -> None:
    """Render the agent result with classification, reply and audit signals."""
    urgency_color = URGENCY_COLOR.get(result.urgency, "gray")
    security_flag = result.label == "SECURITY"
    top_score = result.scores[0] if result.scores else 0.0
    low_confidence = top_score < 0.3

    c1, c2 = st.columns(2)
    c1.markdown(f"**Categoria** &nbsp;&nbsp; :blue[**{result.label}**]")
    c2.markdown(f"**Urgenza** &nbsp;&nbsp; :{urgency_color}[**{result.urgency}**]")

    st.caption(result.summary)

    if security_flag:
        st.warning(
            "**Segnalazione di sicurezza** — questa richiesta e' stata "
            "classificata come incidente di sicurezza e tracciata di "
            "conseguenza nel report di audit."
        )
    if low_confidence:
        st.info(
            "**Confidenza bassa** — la knowledge base contiene poche "
            "informazioni rilevanti per questa richiesta. Potrebbe servire un "
            "intervento manuale o l'aggiunta di nuovi documenti alla KB."
        )

    st.divider()
    st.subheader("Risposta")
    st.markdown(result.reply)

    with st.expander("Dettagli tecnici"):
        st.markdown("**Documenti recuperati dalla knowledge base**")
        for doc_id, score in zip(result.top_k, result.scores):
            st.markdown(f"- `{doc_id}` &nbsp;&nbsp; similarita' `{score:.4f}`")
        st.markdown("**File di report salvati**")
        st.code(result.report_paths["report_json"], language="text")
        st.code(result.report_paths["reply_txt"], language="text")


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
def main() -> None:
    st.session_state.setdefault("query", "")
    st.session_state.setdefault("result", None)

    # ---------- Sidebar ----------
    with st.sidebar:
        st.header("IT Help Desk Agent")
        st.caption(
            "Risposte IT istantanee, basate solo sui documenti aziendali "
            "ufficiali (RAG). Supporta inglese e italiano; la knowledge base "
            "e' in inglese, quindi le risposte piu' precise si ottengono con "
            "domande in inglese."
        )
        st.divider()
        st.subheader("Esempi rapidi")
        st.caption("Clicca per provarli.")
        for i, ex in enumerate(EXAMPLES):
            st.button(
                ex,
                key=f"ex_{i}",
                on_click=_set_query,
                args=(ex,),
                use_container_width=True,
            )
        st.divider()
        st.caption(
            "L'agente classifica la richiesta, recupera dalla knowledge base "
            "i documenti piu' rilevanti e genera una risposta vincolata a "
            "quei documenti. Ogni richiesta viene salvata su disco per audit."
        )

    # ---------- Main area ----------
    st.title("IT Help Desk Support Agent")
    st.write(
        "Descrivi il tuo problema IT — riceverai una risposta basata solo "
        "sui documenti aziendali ufficiali."
    )

    st.text_area(
        "La tua richiesta",
        key="query",
        height=160,
        placeholder="Es. Non riesco a collegarmi alla VPN da casa...",
        label_visibility="collapsed",
    )

    c1, c2, _ = st.columns([2, 1, 4])
    submit = c1.button(
        "Invia richiesta",
        type="primary",
        disabled=not st.session_state["query"].strip(),
        use_container_width=True,
    )
    c2.button("Pulisci", on_click=_clear_all, use_container_width=True)

    if submit:
        message = st.session_state["query"].strip()
        try:
            with st.spinner("Sto analizzando la tua richiesta..."):
                st.session_state["result"] = get_agent().run(message)
        except Exception as exc:
            st.session_state["result"] = None
            st.error(f"Si e' verificato un errore durante l'elaborazione: {exc}")

    if st.session_state["result"] is not None:
        st.divider()
        _render_result(st.session_state["result"])


if __name__ == "__main__":
    main()
