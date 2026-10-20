import streamlit as st
import re
from PIL import Image
import pytesseract

st.set_page_config(page_title="Generator Pontaje", layout="wide")
st.title("⏱️ Generator Automat de Pontaje")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Date brute (Lista 1)")
    uploaded_files = st.file_uploader(
        "Încarcă pozele cu pontaje (opțional):", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )
    raw_text_input = st.text_area(
        "Sau lipește textul brut aici:", 
        height=320, 
        placeholder="Lipește aici textul dacă nu ai poze sau vrei să îl adaugi manual..."
    )

with col2:
    st.subheader("2. Lista țintă cu ID-uri (Lista 2)")
    id_list_input = st.text_area(
        "Lipește lista de ID-uri (inclusiv DELIMITARE):", 
        height=400, 
        placeholder="28463\n32207\nDELIMITARE\n57029"
    )

def parse_time(block_text):
    text = block_text.lower()
    if "fara" in text:
        return "00:00:00"
    
    # Corecții pentru erori frecvente OCR
    text = text.replace('lóh', '16h').replace('th', '7h').replace('ld', '1d')
    
    d = re.search(r'(\d+)\s*d', text)
    h = re.search(r'(\d+)\s*h', text)
    m = re.search(r'(\d+)\s*m', text)

    days = int(d.group(1)) if d else 0
    hours = int(h.group(1)) if h else 0
    minutes = int(m.group(1)) if m else 0

    total_hours = days * 24 + hours
    return f"{total_hours:02d}:{minutes:02d}:00"

def extract_entries(full_text):
    entries = {}
    matches = list(re.finditer(r'\[(\d+)\]', full_text))
    for i, match in enumerate(matches):
        id_val = match.group(1)
        start_idx = match.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[start_idx:end_idx]
        entries[id_val] = parse_time(block)
    return entries

if st.button("🚀 Generează Pontajele", type="primary", use_container_width=True):
    combined_text = ""
    
    if uploaded_files:
        with st.spinner("Se procesează imaginile..."):
            for img_file in uploaded_files:
                img = Image.open(img_file)
                ocr_text = pytesseract.image_to_string(img)
                combined_text += "\n" + ocr_text

    if raw_text_input:
        combined_text += "\n" + raw_text_input

    if not combined_text.strip():
        st.error("Te rog să încarci cel puțin o poză sau să lipești textul brut la Pasul 1.")
    elif not id_list_input.strip():
        st.error("Te rog să introduci ID-urile dorite la Pasul 2.")
    else:
        entries = extract_entries(combined_text)
        output_lines = []
        
        for line in id_list_input.strip().splitlines():
            clean_line = line.strip()
            if not clean_line:
                continue
            if clean_line.upper() == "DELIMITARE":
                output_lines.append("DELIMITARE")
            elif clean_line in entries:
                output_lines.append(entries[clean_line])
            else:
                output_lines.append("LIPSA")
        
        result_text = "\n".join(output_lines)
        
        st.success("Pontajele au fost generate cu succes!")
        st.text_area("Rezultat final (gata de copiat):", value=result_text, height=350)
        st.download_button("📥 Descarcă fișier text (.txt)", result_text, file_name="pontaje.txt")
