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

def parse_time_details(time_str):
    if not time_str or "fara" in str(time_str).lower():
        return "00:00:00", 0
    
    clean = str(time_str).lower().replace('lóh', '16h').replace('th', '7h').replace('ld', '1d')
    
    d = re.search(r'(\d+)\s*d', clean)
    h = re.search(r'(\d+)\s*h', clean)
    m = re.search(r'(\d+)\s*m', clean)
    s = re.search(r'(\d+)\s*s', clean)

    days = int(d.group(1)) if d else 0
    hours = int(h.group(1)) if h else 0
    minutes = int(m.group(1)) if m else 0
    seconds = int(s.group(1)) if s else 0

    total_hours = days * 24 + hours
    total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return f"{total_hours:02d}:{minutes:02d}:00", total_seconds

def extract_from_text(text):
    entries = {}
    matches = list(re.finditer(r'([^\n\r\[]+)?\[(\d+)\]', text))
    for i, match in enumerate(matches):
        raw_name = match.group(1)
        name = raw_name.strip() if raw_name else f"Membru [{match.group(2)}]"
        id_val = match.group(2)
        start_idx = match.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start_idx:end_idx]
        formatted_time, total_secs = parse_time_details(block)
        entries[id_val] = {
            "formatted": formatted_time,
            "seconds": total_secs,
            "name": name,
            "id": id_val
        }
    return entries

def extract_all_with_gemini(images, key):
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-3.8-flash")
    
    prompt = """
    Analizează cu atenție TOATE imaginile furnizate cu pontaje/jurnale de activitate.
    Pentru fiecare utilizator identificat prin Nume [ID], extrage:
    - Numele utilizatorului
    - ID-ul numeric exact (fără paranteze)
    - Durata activității/pontajul (de exemplu: '1d 5h 28m', '14h 35m', '22m', 'fara', etc.)
    
    Răspunde STRICT cu un dicționar JSON valid, fără explicații sau markdown:
    {
      "ID": {"nume": "Nume", "durata": "durata"},
      "altID": {"nume": "Alt Nume", "durata": "durata"}
    }
    Dacă la un ID scrie 'fara', pune valoarea 'fara'.
    Asigură-te că parcurgi toate imaginile și nu omiți niciun ID.
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
        
        # 1. Procesare poze cu Gemini
        if uploaded_files and api_key:
            with st.spinner(f"AI-ul analizează toate cele {len(uploaded_files)} imagini..."):
                try:
                    pil_images = [Image.open(f) for f in uploaded_files]
                    ai_data = extract_all_with_gemini(pil_images, api_key)
                    for k, v in ai_data.items():
                        id_str = str(k).strip()
                        if isinstance(v, dict):
                            name_str = v.get("nume", f"Membru [{id_str}]")
                            dur_str = v.get("durata", "00:00:00")
                        else:
                            name_str = f"Membru [{id_str}]"
                            dur_str = str(v)
                        
                        f_time, secs = parse_time_details(dur_str)
                        all_entries[id_str] = {
                            "formatted": f_time,
                            "seconds": secs,
                            "name": name_str,
                            "id": id_str
                        }
                except Exception as e:
                    st.error(f"Eroare la citirea imaginilor: {e}")

        # 2. Procesare text brut suplimentar (dacă există)
        if raw_text_input.strip():
            text_entries = extract_from_text(raw_text_input)
            all_entries.update(text_entries)

        if not all_entries:
            st.error("Nu s-au putut extrage date. Verifică imaginile sau textul introdus.")
        else:
            # Afișare TOP 5 Cei mai activi
            st.divider()
            st.subheader("🏆 Top 5 Cei Mai Activi Membri")
            
            medals = ["🥇 Locul 1", "🥈 Locul 2", "🥉 Locul 3", "🎖️ Locul 4", "🎖️ Locul 5"]
            sorted_top = sorted(all_entries.values(), key=lambda x: x["seconds"], reverse=True)[:5]
            
            top_cols = st.columns(len(sorted_top))
            top_summary_lines = []
            
            for idx, member in enumerate(sorted_top):
                with top_cols[idx]:
                    st.metric(
                        label=f"{medals[idx]}: {member['name']} [{member['id']}]",
                        value=member["formatted"]
                    )
                top_summary_lines.append(f"{idx+1}. {member['name']} [{member['id']}] - {member['formatted']}")
            
            # Format text rapid de copiat pentru Top 5
            st.caption("Format text rapid pentru Top 5:")
            st.code("\n".join(top_summary_lines), language="text")
            
            st.divider()
            
            # Generare listă mapată pentru Google Sheets (Lista 2)
            output_lines = []
            for line in id_list_input.strip().splitlines():
                clean = line.strip()
                if not clean:
                    continue
                if clean.upper() == "DELIMITARE":
                    output_lines.append("DELIMITARE")
                elif clean in all_entries:
                    output_lines.append(all_entries[clean]["formatted"])
                else:
                    output_lines.append("LIPSA")
            
            result_text = "\n".join(output_lines)
            st.subheader("📋 Lista completă pentru Foaia de Calcul:")
            st.text_area("Rezultat final (gata de copiat):", value=result_text, height=350)
            st.download_button("📥 Descarcă fișier text (.txt)", result_text, file_name="pontaje.txt")
