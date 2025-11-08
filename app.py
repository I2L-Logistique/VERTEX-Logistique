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
st.set_page_config(page_title="VERTEX - Assistant Logistique", layout="centered")

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
    align-self: flex-start; background-color: #F8FAFF;
    border: 1px solid #C7D7ED; padding: 12px 18px;
    border-radius: 16px 16px 16px 2px; max-width: 80%;
    font-size: 16px; word-wrap: break-word;
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
