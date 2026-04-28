import streamlit as st
import io
import re

# --- CORE LOGIC ---
def process_single_file(uploaded_file):
    # Standardizing spaces and encoding to handle non-breaking spaces (\xa0)
    content = uploaded_file.getvalue().decode('cp1255', errors='ignore')
    content = content.replace('\xa0', ' ').replace('\t', ' ')
    
    lines = content.splitlines()
    zone = None
    packages = []
    nets_data = {}
    current_net = None
    
    # Forbidden chars for footprints: / * \ # @ & ^ % ?
    chars_to_remove = r"[/\\*#@&^%?]"

    for line in lines:
        raw_line = line
        line_strip = line.strip()
        if not line_strip: continue
            
        upper_line = line_strip.upper()
        
        # 1. Section Detection
        if any(k in upper_line for k in ["PART", "PACKAGES", "$PACKAGES"]):
            zone = "START"
            continue
        elif any(k in upper_line for k in ["$NETS", "NET"]):
            zone = "END"
            continue
        elif upper_line.startswith('$'):
            zone = None
            continue

        # 2. FOOTPRINTS SECTION
        if zone == "START":
            # Sanitize footprint name: remove parentheses and forbidden chars
            mod_line = re.sub(r'\(.*?\)', '', line_strip)
            mod_line = re.sub(chars_to_remove, "", mod_line)
            mod_line = mod_line.replace('!', ' ').replace(';', ' ')
            parts = mod_line.split()
            
            if len(parts) >= 2:
                pkg_id = parts[0].replace('.', '_').replace(',', '_').upper()
                des = parts[-1]
                val = parts[1] if len(parts) > 2 else ""
                if len(pkg_id) >= 2:
                    packages.append(f"!{pkg_id}! {val}; {des}")

        # 3. NETS SECTION - Reconstruction logic
        elif zone == "END":
            # Replace dash with dot for pins and clean special separators
            clean_line = line_strip.replace('-', '.')
            
            # If line doesn't start with space/tab, it's a Net declaration
            if not raw_line.startswith((' ', '\t')):
                # Split by semicolon to isolate Net Name
                if ';' in clean_line:
                    net_part, pin_part = clean_line.split(';', 1)
                    current_net = net_part.strip()
                    pins = pin_part.replace(',', ' ').split()
                else:
                    parts = clean_line.split()
                    current_net = parts[0]
                    pins = parts[1:]
                
                if current_net:
                    if current_net not in nets_data:
                        nets_data[current_net] = []
                    nets_data[current_net].extend([p for p in pins if p.strip()])
            else:
                # Indented line - continuation of previous net
                if current_net:
                    pins = clean_line.replace(',', ' ').split()
                    nets_data[current_net].extend([p for p in pins if p.strip()])

    # --- BUILDING OUTPUT ---
    final_result = ["$PACKAGES"]
    final_result.extend(packages)
    final_result.append("$NETS")
    
    for net_name, pins in nets_data.items():
        # Filtering empty strings and stray semicolons
        actual_pins = [p.strip() for p in pins if p.strip() and p.strip() != ';']
        if not actual_pins: continue
        
        # Format: NetName; Pin1 Pin2... (Standard Allegro format)
        final_result.append(f"{net_name}; {' '.join(actual_pins)}")
    
    final_result.append("$End")
    return "\n".join(final_result)

# --- UI LAYOUT & STYLING ---
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
