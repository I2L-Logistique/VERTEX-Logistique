import streamlit as st
import os
import pandas as pd
import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI
import re

# ---------------------------
# 1) Récupération API Key
# ---------------------------
def get_api_key():
    try:
        return st.secrets["openai"]["api_key"]
    except Exception:
        load_dotenv()
        return os.getenv("OPENAI_API_KEY")

API_KEY = get_api_key()
if not API_KEY:
    st.error("La clé OpenAI est introuvable. En local : crée un fichier .env avec OPENAI_API_KEY=...  — Sur Streamlit Cloud : ajoute la clé dans Settings → Secrets.")
    st.stop()

client = OpenAI(api_key=API_KEY)

# ---------------------------
# 2) Page config
# ---------------------------
st.markdown("""
<link rel="manifest" href="https://raw.githubusercontent.com/I2L-Logistique/VERTEX-Logistique/main/static/manifest.json">
<meta name="theme-color" content="#004B8D">

<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="VERTEX">
<link rel="apple-touch-icon" href="https://raw.githubusercontent.com/I2L-Logistique/VERTEX-Logistique/main/static/icons/icon-192.PNG">
""", unsafe_allow_html=True)

# ---------------------------
# 3) CSS
# ---------------------------
st.set_page_config(
    page_title="VERTEX - Assistant Logistique",
    page_icon="static/icons/icon-192.png",  # chemin local vers ton icône
    layout="wide"
)


# ---------------------------
# 4) En-tête
# ---------------------------
LOGO_I2L = "i2l_logo.png"
if os.path.exists(LOGO_I2L):
    st.markdown('<div class="logo-center">', unsafe_allow_html=True)
    st.image(LOGO_I2L, width=100)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="big-title">VERTEX</div>', unsafe_allow_html=True)
st.markdown('<div class="small-subtitle">L’assistant IA de l’Ecole d’Ingénieurs I²L pour la logistique :</div>', unsafe_allow_html=True)

# ---------------------------
# 5) Inputs
# ---------------------------
prompt = st.text_input("Votre prompt :", placeholder="Formuler votre prompt logistique", label_visibility="collapsed")
uploaded_file = st.file_uploader("Importer un fichier (PDF, TXT, CSV, XLSX)", type=["pdf", "txt", "csv", "xlsx"])

if "history" not in st.session_state:
    st.session_state.history = []

# ---------------------------
# 6) Extraction texte
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
# 7) Fonction d’affichage propre du texte + LaTeX
# ---------------------------



def render_ai_answer(ai_answer: str):
    """
    Affiche proprement du texte et des équations LaTeX (inline + bloc)
    compatible avec Streamlit Cloud.
    """
    # Nettoyage basique
    ai_answer = ai_answer.strip()
    ai_answer = re.sub(r'\n{2,}', '\n\n', ai_answer)  # garder 2 sauts max

    # Conversion LaTeX : \(...\) -> $...$, \[...\] -> $$...$$
    ai_answer = ai_answer.replace("\\(", "$").replace("\\)", "$")
    ai_answer = ai_answer.replace("\\[", "$$").replace("\\]", "$$")

    # Affichage direct avec st.markdown
    # Laisser Streamlit interpréter le Markdown et LaTeX
    st.markdown(ai_answer, unsafe_allow_html=True)

# ---------------------------
# 8) Envoi à l’API
# ---------------------------
if st.button("Envoyer"):
    if not prompt.strip() and not uploaded_file:
        st.warning("Veuillez saisir un message ou importer un fichier.")
    else:
        with st.spinner("Analyse en cours..."):
            file_text = ""
            if uploaded_file:
                file_text = extract_text_from_file(uploaded_file)

            final_prompt = prompt
            if file_text:
                excerpt = file_text[:30000]
                final_prompt += "\n\nContenu du fichier (extrait):\n" + excerpt

            st.session_state.history.append({"role": "user", "content": final_prompt})

            messages = [{"role": "system", "content": "Tu es VERTEX, expert en logistique, clair, précis et structuré."}]
            for m in st.session_state.history:
                messages.append({"role": m["role"], "content": m["content"]})

            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1500
                )
                ai_answer = response.choices[0].message.content
            except Exception as e:
                ai_answer = f"[Erreur API OpenAI] {e}"

            st.session_state.history.append({"role": "assistant", "content": ai_answer})

# ---------------------------
# 9) Affichage conversation
# ---------------------------
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="chat-bubble-ai">', unsafe_allow_html=True)
        render_ai_answer(msg["content"])
        st.markdown('</div>', unsafe_allow_html=True)
