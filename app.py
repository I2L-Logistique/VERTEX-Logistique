import streamlit as st
import os
import pdfplumber
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------
# 1) Configuration de la page
# ---------------------------
st.set_page_config(page_title="VERTEX", page_icon="public/icons/icon-192.png", layout="wide")

# --- Initialisation KaTeX ---
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.15.0/katex.min.css">
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.15.0/katex.min.js"></script>
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.15.0/contrib/auto-render.min.js"></script>
<script>
  document.addEventListener("DOMContentLoaded", function() {
    renderMathInElement(document.body, {
      delimiters: [
        { left: "$", right: "$", display: false },
        { left: "$$", right: "$$", display: true }
      ]
    });
  });
</script>
""", unsafe_allow_html=True)

# Favicon + manifest
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
    st.error("⚠️ Clé OpenAI manquante. Ajoute-la dans .env ou Settings > Secrets.")
    st.stop()

client = OpenAI(api_key=API_KEY)

# ---------------------------
# 3) Styles CSS
# ---------------------------
st.markdown("""
<style>
body { background-color: #DDEDFC; font-family: 'Inter', sans-serif; }
.big-title { text-align: center; font-size: 90px; font-weight: 900; color: #003B73; margin-bottom: -5px; }
.small-subtitle { text-align: center; font-size: 19px; color: #4A4A4A; margin-top: -10px; margin-bottom: 10px; }
.logo-center { display: flex; justify-content: center; margin-bottom: 20px; }
.stButton > button { background-color: #004B8D; color: white; border-radius: 10px; padding: 10px 26px; font-size: 17px; border: none; font-weight: 600; }
.stButton > button:hover { background-color: #003760; transform: scale(1.02); }
.bubble-user, .bubble-ai {
    padding: 14px 22px;
    border-radius: 14px;
    margin: 10px 0;
    max-width: 90%;
    line-height: 1.6;
    font-size: 16px;
}
.bubble-user {
    background-color: #004B8D;
    color: white;
    margin-left: auto;
    text-align: left;
}
.bubble-ai {
    background-color: #FFFFFF;
    border: 1px solid #C2D8F2;
    box-shadow: 0 4px 8px rgba(0,75,141,0.1);
    color: #001F3F;
    font-family: 'Georgia', serif;
    text-align: justify;
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
st.markdown('<div class="small-subtitle">L’assistant IA de l’Ecole d’Ingénieurs I2L pour la logistique :</div>', unsafe_allow_html=True)

# ---------------------------
# 5) Zone de saisie utilisateur
# ---------------------------
prompt = st.text_area("Votre prompt :", placeholder="Formulez votre requête logistique ici...", label_visibility="collapsed", height=100)
uploaded_file = st.file_uploader("Importer un fichier (PDF, TXT, CSV, XLSX)", type=["pdf", "txt", "csv", "xlsx"])

if "history" not in st.session_state:
    st.session_state.history = []
if "last_prompt" not in st.session_state:
    st.session_state.last_prompt = ""

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
# 7) Affichage des messages
# ---------------------------
def render_message(role, content):
    contains_latex = "$$" in content or "$" in content
    if role == "user":
        st.markdown(f'<div class="bubble-user">{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bubble-ai">{content}</div>', unsafe_allow_html=True)
    if contains_latex:
        st.markdown(""" 
        <script>
        if (window.katex) {
            katex.renderMathInElement(document.body);
        }
        </script>
        """, unsafe_allow_html=True)

# ---------------------------
# 8) Envoi du prompt à GPT
# ---------------------------
def envoyer_message():
    if not prompt.strip() and not uploaded_file:
        st.warning("Veuillez saisir un message ou importer un fichier.")
        return

    with st.spinner(""):
        file_text = ""
        if uploaded_file:
            file_text = extract_text_from_file(uploaded_file)

        final_prompt = prompt
        if file_text:
            excerpt = file_text[:30000]
            final_prompt += "\n\nContenu du fichier (extrait):\n" + excerpt

        final_prompt = (
    "Réponds en Markdown. Si le sujet exige des calculs ou des démonstrations mathématiques, utilise LaTeX pour les équations entre $$ ... $$ et encadre les symboles mathématiques inline par $...$ (ex: $x_{ij}$, $q_i$, $V$). Sinon, réponds uniquement en texte clair, sans équations.\n\n"
    + final_prompt
)



        st.session_state.history.append({"role": "user", "content": prompt})

        try:
            response = client.responses.create(model="gpt-5", input=final_prompt)
            ai_answer = response.output_text.strip()
            if not ai_answer:
                ai_answer = "[Aucune réponse reçue de GPT-5 — possible délai API.]"
        except Exception as e:
            ai_answer = f"[Erreur API OpenAI] {e}"

        st.session_state.history.append({"role": "assistant", "content": ai_answer})

# ---------------------------
# 9) Envoi manuel uniquement
# ---------------------------
if st.button("Envoyer", key="send_button"):
    st.session_state.last_prompt = prompt
    envoyer_message()

# ---------------------------
# 10) Affichage de l'historique
# ---------------------------
for msg in st.session_state.history:
    render_message(msg["role"], msg["content"])
