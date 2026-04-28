import streamlit as st
import io
import re

# --- CORE LOGIC ---
def process_single_file(uploaded_file):
    # Standardizing characters and handling non-breaking spaces (\xa0)
    content = uploaded_file.getvalue().decode('cp1255', errors='ignore')
    content = content.replace('\xa0', ' ').replace('\t', ' ')
    
    lines = content.splitlines()
    zone = None
    final_output = []
    
    forbidden_chars = r"[/\\*#@&^%?]"

    for line in lines:
        raw_line = line
        line_strip = line.strip()
        
        if not line_strip:
            final_output.append("")
            continue
        
        upper_line = line_strip.upper()
        
        # Section Detection
        if any(k in upper_line for k in ["PART", "PACKAGES", "$PACKAGES"]):
            zone = "START"
            final_output.append("$PACKAGES")
            continue
        elif any(k in upper_line for k in ["$NETS", "NET"]):
            zone = "END"
            final_output.append("$NETS")
            continue
        elif upper_line.startswith('$'):
            zone = None
            final_output.append(raw_line)
            continue

        # 1. FOOTPRINTS SECTION
        if zone == "START":
            # Clean parentheses and forbidden chars
            mod_line = re.sub(r'\(.*?\)', '', line_strip)
            mod_line = re.sub(forbidden_chars, "", mod_line)
            mod_line = mod_line.replace('!', ' ').replace(';', ' ')
            parts = mod_line.split()
            if len(parts) >= 2:
                pkg_id = parts[0].replace('.', '_').replace(',', '_').upper()
                des = parts[-1]
                val = parts[1] if len(parts) > 2 else ""
                final_output.append(f"!{pkg_id}! {val}; {des}")

        # 2. NETS SECTION - Direct Character Replacement
        elif zone == "END":
            # Replace dash with dot ONLY (to preserve names like GND, E, B, H4)
            mod_line = raw_line.replace('-', '.')
            # Replace commas with spaces (for multi-line pins)
            mod_line = mod_line.replace(',', ' ')
            # Ensure the semicolon has a space after it if it's followed by text
            mod_line = re.sub(r';(\S)', r'; \1', mod_line)
            final_output.append(mod_line)
            
        else:
            final_output.append(raw_line)

    return "\n".join(final_output)

# --- UI LAYOUT ---
st.set_page_config(page_title="Mind-Board Converter", layout="wide")
logo_url = "https://raw.githubusercontent.com/yurko120/netlist-converter/main/.devcontainer/MindBoard-Logo.jpg"

st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("{logo_url}");
        background-repeat: no-repeat; background-attachment: fixed;
        background-position: center 70%; background-size: 45%; 
    }}
    .stApp::before {{
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(255, 255, 255, 0.92); z-index: -1;
    }}
    .centered-title {{
        text-align: center; color: #000000; font-size: 2.8em !important; 
        font-weight: 900 !important; margin-bottom: 20px !important;
    }}
    .stTextArea textarea {{
        background-color: rgba(255, 255, 255, 0.6) !important; 
        border: 2px solid #000000 !important;
        font-family: 'Courier New', monospace; font-weight: 800 !important; 
    }}
    </style>
    <h1 class="centered-title">Mind-Board Converter</h1>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("### **1. Upload Source Files**")
    uploaded_files = st.file_uploader("Upload .NET files", accept_multiple_files=True, label_visibility="collapsed")

if uploaded_files:
    processed_files_data = []
    with col2:
        st.markdown("### **2. File Settings & Download**")
        for idx, f in enumerate(uploaded_files):
            with st.container():
                st.markdown(f"**Original File:** `{f.name}`")
                original_name = f.name.rsplit('.', 1)[0]
                custom_name = st.text_input("Enter Output Name:", value=f"{original_name}_transformed", key=f"name_input_{idx}")
                content = process_single_file(f)
                processed_files_data.append({"display_name": custom_name, "content": content})
                full_filename = custom_name if custom_name.endswith(('.txt', '.net')) else f"{custom_name}.txt"
                st.download_button(label=f"📥 Download {full_filename}", data=content, file_name=full_filename, mime="text/plain", key=f"dl_btn_{idx}", use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🔍 Technical Preview")
    tab_titles = [item["display_name"] for item in processed_files_data]
    if tab_titles:
        tabs = st.tabs(tab_titles)
        for idx, tab in enumerate(tabs):
            with tab:
                st.text_area(f"Preview: {processed_files_data[idx]['display_name']}", value=processed_files_data[idx]['content'], height=450, key=f"preview_text_{idx}")
