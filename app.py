import streamlit as st
import re
import json
from PIL import Image
import google.generativeai as genai

st.set_page_config(page_title="Generator Pontaje cu AI", layout="wide")
st.title("⏱️ Generator Automat de Pontaje (AI Vision)")

# Bara laterală pentru cheia API
st.sidebar.header("🔑 Setări AI")
api_key = st.sidebar.text_input(
    "Lipește Cheia Gemini API:", 
    type="password", 
    help="Cheia generată gratuit din Google AI Studio"
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Date brute (Imagini sau Text)")
    uploaded_files = st.file_uploader(
        "Încarcă screenshot-urile cu pontaje:", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )
    raw_text_input = st.text_area(
        "Sau lipește textul brut aici (opțional):", 
        height=260, 
        placeholder="Lipește textul brut dacă îl ai deja copiat..."
    )

with col2:
    st.subheader("2. Lista țintă cu ID-uri (Lista 2)")
    id_list_input = st.text_area(
        "Lipește lista de ID-uri (inclusiv DELIMITARE):", 
        height=380, 
        placeholder="28463\n32207\nDELIMITARE\n57029"
    )

def parse_time_string(time_str):
    if not time_str or "fara" in str(time_str).lower():
        return "00:00:00"
    
    clean = str(time_str).lower().replace('lóh', '16h').replace('th', '7h').replace('ld', '1d')
    
    d = re.search(r'(\d+)\s*d', clean)
    h = re.search(r'(\d+)\s*h', clean)
    m = re.search(r'(\d+)\s*m', clean)

    days = int(d.group(1)) if d else 0
    hours = int(h.group(1)) if h else 0
    minutes = int(m.group(1)) if m else 0

    total_hours = days * 24 + hours
    return f"{total_hours:02d}:{minutes:02d}:00"

def extract_from_text(text):
    entries = {}
    matches = list(re.finditer(r'\[(\d+)\]', text))
    for i, match in enumerate(matches):
        id_val = match.group(1)
        start_idx = match.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start_idx:end_idx]
        entries[id_val] = parse_time_string(block)
    return entries

def extract_with_gemini(images, key):
    genai.configure(api_key=key)
    
    # Modelul cerut de Google
    model = genai.GenerativeModel("gemini-3.8-flash")
    
    prompt = """
    Analizează cu atenție imaginile cu pontaje/jurnale de activitate.
    Pentru fiecare utilizator/jucător identificat prin [ID] (numărul din paranteze drepte, de exemplu [15330]), extrage:
    - ID-ul numeric exact (fără paranteze)
    - Durata activității/pontajul (de exemplu: '1d 5h 28m', '14h 35m', '22m', 'fara', etc.)
    
    Răspunde STRICT cu un dicționar JSON valid, fără explicații sau formatare markdown:
    {"ID": "durata", "altID": "durata"}
    Dacă scrie 'fara', pune 'fara'.
    """
    
    content = [prompt] + images
    response = model.generate_content(content)
    
    text = response.text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    
    return json.loads(text)

if st.button("🚀 Generează Pontajele", type="primary", use_container_width=True):
    if not id_list_input.strip():
        st.error("Te rog să introduci lista de ID-uri la Pasul 2.")
    elif uploaded_files and not api_key:
        st.error("Te rog să introduci cheia Google Gemini API în bara laterală din stânga!")
    else:
        all_entries = {}
        
        # 1. Procesare poze cu Gemini AI
        if uploaded_files and api_key:
            with st.spinner("AI-ul citește imaginile cu Gemini 3.8 Flash..."):
                try:
                    pil_images = [Image.open(f) for f in uploaded_files]
                    ai_data = extract_with_gemini(pil_images, api_key)
                    for k, v in ai_data.items():
                        all_entries[str(k).strip()] = parse_time_string(v)
                except Exception as e:
                    st.error(f"Eroare la citirea imaginilor cu AI: {e}")

        # 2. Procesare text brut suplimentar (dacă există)
        if raw_text_input.strip():
            text_entries = extract_from_text(raw_text_input)
            all_entries.update(text_entries)

        if not all_entries:
            st.error("Nu s-au putut extrage date. Verifică imaginile sau textul introdus.")
        else:
            output_lines = []
            for line in id_list_input.strip().splitlines():
                clean = line.strip()
                if not clean:
                    continue
                if clean.upper() == "DELIMITARE":
                    output_lines.append("DELIMITARE")
                elif clean in all_entries:
                    output_lines.append(all_entries[clean])
                else:
                    output_lines.append("LIPSA")
            
            result_text = "\n".join(output_lines)
            st.success("Pontajele au fost generate cu succes!")
            st.text_area("Rezultat final (gata de copiat):", value=result_text, height=350)
            st.download_button("📥 Descarcă fișier text (.txt)", result_text, file_name="pontaje.txt")
