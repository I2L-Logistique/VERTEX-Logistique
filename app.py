# VERTEX.py
import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import pdfplumber

# ---------------------------
# 1) Récupération de la clé
# ---------------------------
def get_api_key():
    # 1) d'abord essayer st.secrets (Streamlit Cloud)
    try:
        # Format attendu in app secrets: 
        # [openai]
        # api_key = "sk-..."
        return st.secrets["openai"]["api_key"]
    except Exception:
        # 2) fallback local : .env
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
st.set_page_config(page_title="Posez votre question logistique", layout="centered")



# ---------------------------
# 4) CSS (couleurs + bulles)
# ---------------------------
st.markdown("""
<style>
/* Layout */
body {
    background-color: #DDEDFC;
    font-family: 'Inter', sans-serif;
}

/* Positionnement du logo : on le remet en haut à droite via une classe conteneur */
.header {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
}

/* On placera le logo visuellement top-right via margin-left: auto on small header container below */
.header img {
    position: absolute;
    right: 30px;
    top: 10px;
}

/* Titres */
.title {
    text-align: center;
    font-size: 30px;
    font-weight: 700;
    color: #003B73;
    margin-bottom: 6px;
}
.subtitle {
    text-align: center;
    font-size: 18px;
    color: #4A4A4A;
    margin-top: 0px;
    margin-bottom: 18px;
}

/* Chat container and bubbles */
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 14px;
    margin-top: 18px;
    padding-bottom: 20px;
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

.chat-bubble-ai {
    align-self: flex-start;
    background-color: #F8FAFF;
    border: 1px solid #C7D7ED;
    padding: 12px 18px;
    border-radius: 16px 16px 16px 2px;
    max-width: 70%;
    font-size: 16px;
    word-wrap: break-word;
}

/* Input styles */
.stTextInput > div > input {
    border-radius: 10px;
    border: 1px solid #A9BCCD;
    padding: 10px;
    background-color: #FFFFFF;
}

/* Button styles */
.stButton > button {
    background-color: #004B8D;
    color: white;
    border-radius: 10px;
    padding: 10px 26px;
    font-size: 17px;
    border: none;
    font-weight: 600;
    transition: 0.18s;
}
.stButton > button:hover {
    background-color: #003760;
    transform: scale(1.02);
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------
# 5) Nouveau Header (VERTEX + Sous-titre + Logo I2L)
# ---------------------------

LOGO_I2L = "i2l_logo.png"  # Le fichier doit être dans le même dossier que VERTEX.py

st.markdown("""
<style>
.big-title {
    text-align: center;
    font-size: 90px;  /* ← taille agrandie */
    font-weight: 900;
    color: #003B73;
    margin-bottom: -5px;
}

.small-subtitle {
    text-align: center;
    font-size: 19px;
    color: #4A4A4A;
    margin-top: -10px;  /* Réduit l'espace au-dessus du sous-titre */
    margin-bottom: 5px; /* Réduit l’espace avant le logo */
}
.logo-center {
    display: flex;
    justify-content: center;
    margin-top: -5px; /* Réduit encore l’espace avant le logo */
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# Affichage du logo en haut
if os.path.exists(LOGO_I2L):
    st.markdown('<div class="logo-center">', unsafe_allow_html=True)
    st.image(LOGO_I2L, width=100)  # ← plus petit
    st.markdown('</div>', unsafe_allow_html=True)

# Titre + texte
st.markdown('<div class="big-title">VERTEX</div>', unsafe_allow_html=True)
st.markdown('<div class="small-subtitle">L’assistant IA de l’Ecole d’Ingénieurs I²L de Metz pour la logistique : </div>', unsafe_allow_html=True)

# ---------------------------
# 6) Input + uploader
# ---------------------------
prompt = st.text_input("Votre prompt :", placeholder="Formuler votre prompt logistique pour VERTEX", label_visibility="collapsed")

uploaded_file = st.file_uploader("Importer un fichier (PDF, TXT, CSV, XLSX)", 
                                 type=["pdf", "txt", "csv", "xlsx"])

# ---------------------------
# 7) Conversation state
# ---------------------------
if "history" not in st.session_state:
    # message objects: {"role": "user"/"assistant", "content": "<texte>"}
    st.session_state.history = []

# ---------------------------
# 8) Helper: read uploaded files to text
# ---------------------------
def extract_text_from_file(uploaded):
    text = ""
    try:
        # type detection can vary by browser; check extension fallback
        name = uploaded.name.lower()
        if name.endswith(".txt") or uploaded.type == "text/plain":
            text = uploaded.read().decode(errors="ignore")
        elif name.endswith(".csv") or uploaded.type == "text/csv":
            df = pd.read_csv(uploaded)
            text = df.to_string()
        elif name.endswith(".xlsx") or name.endswith(".xls") or uploaded.type in [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ]:
            df = pd.read_excel(uploaded)
            text = df.to_string()
        elif name.endswith(".pdf") or uploaded.type == "application/pdf":
            with pdfplumber.open(uploaded) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        else:
            # Try to read as text fallback
            try:
                text = uploaded.read().decode(errors="ignore")
            except Exception:
                text = f"[Impossible de lire le fichier {uploaded.name}]"
    except Exception as e:
        text = f"[Erreur lors de la lecture du fichier: {e}]"
    return text

# ---------------------------
# 9) Send button -> call API
# ---------------------------
if st.button("Envoyer"):
    if not prompt.strip() and not uploaded_file:
        st.warning("Veuillez saisir un message ou importer un fichier.")
    else:
        with st.spinner("Analyse en cours..."):
            file_text = ""
            if uploaded_file:
                file_text = extract_text_from_file(uploaded_file)

            # final prompt: keep content short for history: we'll store user's raw question separately
            final_prompt = prompt
            if file_text:
                # trim large files to avoid huge token usage, keep first N chars
                MAX_CHARS = 30_000  # adjust as needed
                excerpt = file_text[:MAX_CHARS]
                final_prompt = final_prompt + "\n\nContenu du fichier (extrait):\n" + excerpt

            # Append user's message (we store only the prompt or final_prompt)
            st.session_state.history.append({"role": "user", "content": final_prompt})

            # Build messages for API: include system + all conversation messages in history
            messages = [{"role": "system", "content": "Tu es VERTEX, expert en logistique, clair et structuré."}]
            # Convert history entries into chat roles expected by API
            for m in st.session_state.history:
                messages.append({"role": m["role"], "content": m["content"]})

            # Call the OpenAI chat completions
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1000
                )
                ai_answer = response.choices[0].message.content
            except Exception as e:
                ai_answer = f"[Erreur API OpenAI] {e}"

            st.session_state.history.append({"role": "assistant", "content": ai_answer})

# ---------------------------
# 10) Render chat bubbles
# ---------------------------
if st.session_state.history:
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for msg in st.session_state.history:
        bubble = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-ai"
        # Use markdown to preserve simple line breaks
        content = msg["content"].replace("\n", "<br>")
        st.markdown(f"<div class='{bubble}'>{content}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


