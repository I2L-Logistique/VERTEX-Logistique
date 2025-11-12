import streamlit as st
import os
import pandas as pd
import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI
import re

# ---------------------------
# 1) Configuration de la page
# ---------------------------
st.set_page_config(
    page_title="VERTEX",
    page_icon="public/icons/icon-192.png",
    layout="wide"
)

# Liens manifest + favicon
st.markdown("""
<link rel="icon" type="image/png" sizes="192x192" href="public/icons/icon-192.png">
<link rel="icon" type="image/png" sizes="512x512" href="public/icons/icon-512.png">
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#004B8D">
""", unsafe_allow_html=True)

# ---------------------------
# 2) Chargement de la clé API
# ---------------------------
def get_api_key():
    try:
        return st.secrets["openai"]["api_key"]
    except Exception:
        load_dotenv()
        return os.getenv("OPENAI_API_KEY")

API_KEY = get_api_key()
if not API_KEY:
    st.error("⚠️ Clé OpenAI manquante. Ajoute-la dans ton fichier .env ou dans Settings > Secrets.")
    st.stop()

client = OpenAI(api_key=API_KEY)

# ---------------------------
# 3) Styles CSS
# ---------------------------
st.markdown("""
<style>
body {
    background-color: #DDEDFC;
    font-family: 'Inter', sans-serif;
}
.big-title {
    text-align: center;
    font-size: 90px;
    font-weight: 900;
    color: #003B73;
    margin-bottom: -5px;
}
.small-subtitle {
    text-align: center;
    font-size: 19px;
    color: #4A4A4A;
    margin-top: -10px;
    margin-bottom: 10px;
}
.logo-center {
    display: flex;
    justify-content: center;
    margin-bottom: 20px;
}
.stButton > button {
    background-color: #004B8D;
    color: white;
    border-radius: 10px;
    padding: 10px 26px;
    font-size: 17px;
    border: none;
    font-weight: 600;
}
.stButton > button:hover {
    background-color: #003760;
    transform: scale(1.02);
}
.chat-bubble-user {
    align-self: flex-end;
    background-color: #004B8D;
    color: white;
    padding: 12px 18px;
    border-radius: 16px 16px 2px 16px;
    max-width: 70%;
    font-size: 16px;
    word-wrap: break-word;
}
.pdf-block {
    background-color: #F7FAFE;
    border: 1px solid #C2D8F2;
    border-radius: 12px;
    padding: 40px 50px;
    margin-top: 25px;
    font-family: 'Georgia', serif;
    font-size: 18px;
    line-height: 1.7;
    color: #001F3F;
    text-align: justify;
    box-shadow: 0 4px 8px rgba(0, 75, 141, 0.1);
}
.pdf-title {
    font-size: 28px;
    font-weight: 800;
    color: #004B8D;
    text-align: center;
    margin-bottom: 25px;
    font-family: 'Georgia', serif;
}
h2, h3 {
    color: #004B8D;
    font-family: 'Georgia', serif;
    margin-top: 25px;
    margin-bottom: 10px;
}
ul {
    margin-left: 25px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# 4) En-tête principale
# ---------------------------
LOGO_I2L = "i2l_logo.png"
if os.path.exists(LOGO_I2L):
    st.markdown('<div class="logo-center">', unsafe_allow_html=True)
    st.image(LOGO_I2L, width=100)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="big-title">VERTEX</div>', unsafe_allow_html=True)
st.markdown('<div class="small-subtitle">L’assistant IA de l’Ecole d’Ingénieurs I²L pour la logistique :</div>', unsafe_allow_html=True)

# ---------------------------
# 5) Zone de saisie utilisateur
# ---------------------------
prompt = st.text_input("Votre prompt :", placeholder="Formuler votre prompt logistique", label_visibility="collapsed")
uploaded_file = st.file_uploader("Importer un fichier (PDF, TXT, CSV, XLSX)", type=["pdf", "txt", "csv", "xlsx"])

if "history" not in st.session_state:
    st.session_state.history = []

# ---------------------------
# 6) Extraction du texte
# ---------------------------
def extract_text_from_file(uploaded):
    text = ""
    try:
        name = uploaded.name.lower()
        if name.endswith(".txt"):
            text = uploaded.read().decode(errors="ignore")
        elif name.endswith(".csv"):
            df = pd.read_csv(uploaded)
            text = df.to_string()
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(uploaded)
            text = df.to_string()
        elif name.endswith(".pdf"):
            with pdfplumber.open(uploaded) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        else:
            text = uploaded.read().decode(errors="ignore")
    except Exception as e:
        text = f"[Erreur lors de la lecture du fichier: {e}]"
    return text

# ---------------------------
# 7) Affichage façon "document PDF"
# ---------------------------
 
def render_ai_answer(answer_text: str):
    """
    Affiche la réponse de l'IA en format enrichi :
    - Markdown (titres, listes, gras, etc.)
    - LaTeX (équations mathématiques)
    """
    st.markdown("""
    <script>
    MathJax = {
      tex: {inlineMath: [['$', '$'], ['\\\\(', '\\\\)']]},
      svg: {fontCache: 'global'}
    };
    </script>
    <script type="text/javascript" async
      src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js">
    </script>
    """, unsafe_allow_html=True)

    st.markdown('<div class="pdf-block">', unsafe_allow_html=True)
    st.markdown(answer_text, unsafe_allow_html=False)
    st.markdown('</div>', unsafe_allow_html=True)
# ---------------------------
# 8) Envoi du prompt à GPT
# ---------------------------
if st.button("Envoyer"):
    if not prompt.strip() and not uploaded_file:
        st.warning("Veuillez saisir un message ou importer un fichier.")
    else:
        with st.spinner("Analyse en cours avec GPT-5..."):
            file_text = ""
            if uploaded_file:
                file_text = extract_text_from_file(uploaded_file)
            final_prompt = prompt
            if file_text:
                excerpt = file_text[:30000]
                final_prompt += "\n\nContenu du fichier (extrait):\n" + excerpt
            st.session_state.history.append({"role": "user", "content": final_prompt})
            try:
                response = client.responses.create(
                model="gpt-5",
                input=final_prompt
                 )
                ai_answer = response.output_text.strip()
                if not ai_answer:
                    ai_answer = "[Aucune réponse reçue de GPT-5 — possible délai API.]"
            except Exception as e:
                ai_answer = f"[Erreur API OpenAI] {e}"
            st.session_state.history.append({"role": "assistant", "content": ai_answer})

# ---------------------------
# 9) Affichage final (bloc unique formaté)
# ---------------------------
if st.session_state.history:
    last_ai_message = next(
        (m["content"] for m in reversed(st.session_state.history) if m["role"] == "assistant"),
        None
    )
    if last_ai_message:
        render_ai_answer(last_ai_message)
