import streamlit as st
import os
import base64
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import pdfplumber

client = OpenAI(api_key=st.secrets["openai"]["api_key"])
# Configuration
st.set_page_config(page_title="Posez votre question logistique", layout="centered")

# Convertir logo en Base64 pour affichage fiable
def load_base64_image(image_path):
    with open(image_path, "rb") as img:
        return base64.b64encode(img.read()).decode()

logo_path = r"C:\Users\kalbouss1-admin\Downloads\VERTEX\vertex_logo.png"
logo_base64 = load_base64_image(logo_path)

# === CSS COMPLET ===
st.markdown(f"""
<style>
body {{
    background-color: #DDEDFC;   /* <<< bleu ciel doux */
    font-family: 'Inter', sans-serif;
}}

.logo {{
    position: absolute;
    top: 20px;
    right: 30px;
}}

.title {{
    text-align: center;
    font-size: 30px;
    font-weight: 700;
    color: #003B73;
}}

.subtitle {{
    text-align: center;
    font-size: 18px;
    color: #4A4A4A;
    margin-bottom: 30px;
}}

.chat-container {{
    display: flex;
    flex-direction: column;
    gap: 14px;
    margin-top: 25px;
}}

.chat-bubble-user {{
    align-self: flex-end;
    background-color: #004B8D;
    color: white;
    padding: 12px 18px;
    border-radius: 16px 16px 2px 16px;
    max-width: 70%;
    font-size: 16px;
}}

.chat-bubble-ai {{
    align-self: flex-start;
    background-color: #F8FAFF;
    border: 1px solid #C7D7ED;
    padding: 12px 18px;
    border-radius: 16px 16px 16px 2px;
    max-width: 70%;
    font-size: 16px;
}}

.stTextInput > div > input {{
    border-radius: 10px;
    border: 1px solid #A9BCCD;
    padding: 10px;
    background-color: #FFFFFF;
}}

.stButton > button {{
    background-color: #004B8D;
    color: white;
    border-radius: 10px;
    padding: 10px 26px;
    font-size: 17px;
    border: none;
    font-weight: 600;
    transition: 0.3s;
}}

.stButton > button:hover {{
    background-color: #003760;
    transform: scale(1.02);
    cursor: pointer;
}}
</style>

<img class="logo" src="data:image/png;base64,{logo_base64}" width="70">
""", unsafe_allow_html=True)

# === TITRES ===
st.markdown('<div class="title">Posez votre question logistique</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Formulez un prompt logistique pour VERTEX</div>', unsafe_allow_html=True)

# Zone de texte
prompt = st.text_input("", placeholder="Écrire un message...")

# Upload fichiers
uploaded_file = st.file_uploader("Importer un fichier (PDF, TXT, CSV, XLSX)", 
                                 type=["pdf", "txt", "csv", "xlsx"])

# Historique conversationnel
if "history" not in st.session_state:
    st.session_state.history = []

# === ACTION BOUTON ENVOYER ===
if st.button("Envoyer"):
    if not prompt.strip() and not uploaded_file:
        st.warning("Veuillez saisir un message ou importer un fichier.")
    else:
        with st.spinner("Analyse en cours..."):
            file_text = ""

            if uploaded_file:
                if uploaded_file.type == "text/plain":
                    file_text = uploaded_file.read().decode()

                elif uploaded_file.type == "text/csv":
                    df = pd.read_csv(uploaded_file)
                    file_text = df.to_string()

                elif uploaded_file.type in [
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ]:
                    df = pd.read_excel(uploaded_file)
                    file_text = df.to_string()

                elif uploaded_file.type == "application/pdf":
                    with pdfplumber.open(uploaded_file) as pdf:
                        for page in pdf.pages:
                            file_text += (page.extract_text() or "") + "\n"

            final_prompt = prompt + (f"\n\nContenu du fichier :\n{file_text}" if file_text else "")

            st.session_state.history.append({"role": "user", "content": final_prompt})

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Tu es VERTEX, expert en logistique, clair et structuré."},
                    *st.session_state.history
                ],
                temperature=0.2
            )

            ai_answer = response.choices[0].message.content
            st.session_state.history.append({"role": "assistant", "content": ai_answer})

# === AFFICHAGE CHAT ===
if st.session_state.history:
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for msg in st.session_state.history:
        bubble = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-ai"
        st.markdown(f"<div class='{bubble}'>{msg['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
