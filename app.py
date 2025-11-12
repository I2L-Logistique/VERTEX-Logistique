import streamlit as st
import os
import pandas as pd
import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI
import re

import streamlit as st

# --- Page config avec favicon ---
st.set_page_config(
    page_title="VERTEX",
    page_icon="public/icons/icon-192.png",  # ton icône personnalisée
    layout="wide"
)

# --- Ajouter le favicon explicitement dans le HTML ---


st.markdown("""
<link rel="icon" type="image/png" sizes="192x192" href="public/icons/icon-192.png">
<link rel="icon" type="image/png" sizes="512x512" href="public/icons/icon-512.png">
""", unsafe_allow_html=True)


# --- Injecter le manifest et les icônes ---
st.markdown("""
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#004B8D">
""", unsafe_allow_html=True)



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


# ---------------------------
# 3) CSS
# ---------------------------
st.markdown("""
<style>
body { background-color: #DDEDFC; font-family: 'Inter', sans-serif; }
.chat-bubble-user {
    align-self: flex-end; background-color: #004B8D; color: white;
    padding: 12px 18px; border-radius: 16px 16px 2px 16px;
    max-width: 70%; font-size: 16px; word-wrap: break-word;
}
.chat-bubble-ai {
    background-color: #DDEDFC;  /* Bleu ciel */
    border: 1px solid #B0CDEB;
    padding: 20px 24px;
    border-radius: 18px;
    max-width: 95%;
    width: auto;
    font-size: 17px;
    word-wrap: break-word;
    margin: 10px auto;
    box-shadow: 0 2px 6px rgba(0, 75, 141, 0.1);
}

.stButton > button {
    background-color: #004B8D; color: white; border-radius: 10px;
    padding: 10px 26px; font-size: 17px; border: none; font-weight: 600;
}
.stButton > button:hover { background-color: #003760; transform: scale(1.02); }
.big-title { text-align: center; font-size: 90px; font-weight: 900; color: #003B73; margin-bottom: -5px; }
.small-subtitle { text-align: center; font-size: 19px; color: #4A4A4A; margin-top: -10px; margin-bottom: 10px; }
.logo-center { display: flex; justify-content: center; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

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


def render_ai_answer(ai_answer: str) -> str:
    """
    Formate proprement la réponse AI pour Streamlit :
    - Texte + LaTeX
    - Sauts de ligne correctement affichés
    - Encadré bleu ciel avec bordure et ombre
    """
    import re

    # Nettoyage basique
    ai_answer = ai_answer.strip()
    ai_answer = re.sub(r'\n{2,}', '\n\n', ai_answer)  # garder max 2 sauts

    # Conversion LaTeX
    ai_answer = ai_answer.replace("\\(", "$").replace("\\)", "$")
    ai_answer = ai_answer.replace("\\[", "$$").replace("\\]", "$$")

    # Remplacer sauts de ligne par <br> pour HTML
    ai_answer = ai_answer.replace("\n", "<br>")

    # HTML pour le "chat bubble"
    html = f"""
    <div class="chat-bubble-ai">
        {ai_answer}
    </div>
    """
    return html



# ---------------------------
# 8) Envoi à l’API
# ---------------------------

if st.button("Envoyer"):
    if not prompt.strip() and not uploaded_file:
        st.warning("Veuillez saisir un message ou importer un fichier.")
    else:
        with st.spinner("Analyse en cours avec GPT-5"):
            file_text = ""
            if uploaded_file:
                file_text = extract_text_from_file(uploaded_file)

            final_prompt = prompt
            if file_text:
                excerpt = file_text[:30000]
                final_prompt += "\n\nContenu du fichier (extrait):\n" + excerpt

            st.session_state.history.append({"role": "user", "content": final_prompt})

            try:
                # Appel GPT-5 avec la méthode officielle adaptée
                response = client.responses.create(
                    model="gpt-5",
                    input=final_prompt
                )
                ai_answer = response.output_text.strip()

                if not ai_answer:
                    ai_answer = "[Aucune réponse reçue de GPT-5 — possible bug temporaire.]"

            except Exception as e:
                ai_answer = f"[Erreur API OpenAI] {e}"

            st.session_state.history.append({"role": "assistant", "content":  ai_answer})

    

# ---------------------------
# 9) Affichage conversation
# ---------------------------
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        # Récupérer HTML complet formaté et l’afficher d’un coup
        answer_html = render_ai_answer(msg["content"])
        st.markdown(answer_html, unsafe_allow_html=True)
