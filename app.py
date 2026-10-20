import streamlit as st
import re
import json
import time
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
    st.subheader("1. Date brute (Toate pozele sau Text)")
    uploaded_files = st.file_uploader(
        "Încarcă TOATE screenshot-urile (poți pune oricâte):", 
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
        placeholder="32207\n15330\nDELIMITARE\n28494"
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

def call_gemini_batch(images, model):
    prompt = """
    Analizează cu atenție imaginile cu pontaje/jurnale de activitate.
    Pentru fiecare utilizator/jucător identificat prin [ID] (numărul din paranteze drepte, de exemplu [15330] sau [32207]), extrage:
    - ID-ul numeric exact (fără paranteze)
    - Durata activității/pontajul (de exemplu: '1d 5h 28m', '14h 35m', '22m', 'fara', etc.)
    
    Răspunde STRICT cu un dicționar JSON valid, fără explicații sau formatare markdown:
    {"ID": "durata", "altID": "durata"}
    Dacă scrie 'fara', pune 'fara'.
    """
    
    # Încercăm de până la 3 ori dacă dă cotă 429
    for attempt in range(3):
        try:
            content = [prompt] + images
            response = model.generate_content(content)
            text = response.text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```[a-zA-Z]*\n", "", text)
                text = re.sub(r"\n```$", "", text)
            return json.loads(text)
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                time.sleep(20)  # Așteaptă 20s să se reseteze cota gratuită
            else:
                raise e
    return {}

if st.button("🚀 Generează Pontajele", type="primary", use_container_width=True):
    if not id_list_input.strip():
        st.error("Te rog să introduci lista de ID-uri la Pasul 2.")
    elif uploaded_files and not api_key:
        st.error("Te rog să introduci cheia Google Gemini API în bara laterală din stânga!")
    else:
        all_entries = {}
        
        # 1. Procesare poze pe loturi automate
        if uploaded_files and api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-3.8-flash")
            
            BATCH_SIZE = 5  # Trimite câte 5 poze pe rând
            total_batches = (len(uploaded_files) + BATCH_SIZE - 1) // BATCH_SIZE
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            pil_images = [Image.open(f) for f in uploaded_files]
            
            for b_idx in range(total_batches):
                start = b_idx * BATCH_SIZE
                end = min(start + BATCH_SIZE, len(pil_images))
                current_batch = pil_images[start:end]
                
                status_text.info(f"⏳ Se procesează lotul {b_idx + 1} din {total_batches} ({len(current_batch)} imagini)...")
                
                try:
                    batch_data = call_gemini_batch(current_batch, model)
                    for k, v in batch_data.items():
                        all_entries[str(k).strip()] = parse_time_string(v)
                except Exception as e:
                    st.error(f"Eroare la lotul {b_idx + 1}: {e}")
                
                progress_bar.progress((b_idx + 1) / total_batches)
                
                # Pauză scurtă între cereri pentru a proteja limita gratuită
                if b_idx < total_batches - 1:
                    time.sleep(14)
            
            status_text.empty()
            progress_bar.empty()

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
            st.success(f"Gata! Au fost găsite {len(all_entries)} pontaje unice în imagini.")
            st.text_area("Rezultat final (gata de copiat în foaia de calcul):", value=result_text, height=350)
            st.download_button("📥 Descarcă fișier text (.txt)", result_text, file_name="pontaje.txt")
