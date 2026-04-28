import streamlit as st
import io
import re

# --- CORE LOGIC ---
def process_single_file(uploaded_file):
    # Standardizing spaces and encoding
    content = uploaded_file.getvalue().decode('cp1255', errors='ignore')
    # Replace non-breaking spaces and tabs with standard spaces
    content = content.replace('\xa0', ' ').replace('\t', ' ')
    
    lines = content.splitlines()
    zone = None
    packages = []
    nets_data = {}
    current_net = None
    
    chars_to_remove = r"[/\\*#@&^%?]"

    for line in lines:
        raw_line = line
        line_strip = line.strip()
        if not line_strip: continue
            
        upper_line = line_strip.upper()
        
        # Section Detection
        if any(k in upper_line for k in ["PART", "PACKAGES", "$PACKAGES"]):
            zone = "START"
            continue
        elif any(k in upper_line for k in ["$NETS", "NET"]):
            zone = "END"
            continue
        elif upper_line.startswith('$'):
            zone = None
            continue

        # 1. FOOTPRINTS SECTION
        if zone == "START":
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

        # 2. NETS SECTION - Robust handling for multi-line and special pins
        elif zone == "END":
            # Clean comma and replace dash with dot for pins
            clean_line = line_strip.replace(',', ' ').replace('-', '.')
            parts = clean_line.split()
            if not parts: continue

            # Logic to determine if this is a new Net or continuation
            # If the original line doesn't start with space, it's a new Net name
            if not raw_line.startswith(' '):
                # The first part is the Net Name (remove semicolon)
                current_net = parts[0].replace(';', '')
                if current_net not in nets_data:
                    nets_data[current_net] = []
                # The rest are pins
                nets_data[current_net].extend([p for p in parts[1:] if p != ';'])
            else:
                # Indented line - add pins to the current active net
                if current_net:
                    nets_data[current_net].extend([p for p in parts if p != ';'])

    # Building Final Output
    final_result = ["$PACKAGES"]
    final_result.extend(packages)
    final_result.append("$NETS")
    
    for net_name, pins in nets_data.items():
        actual_pins = [p.strip() for p in pins if p.strip() and p.strip() != ';']
        if not actual_pins: continue
        # Output exactly in the format: NetName; Pin1 Pin2...
        final_result.append(f"{net_name}; {' '.join(actual_pins)}")
    
    final_result.append("$End")
    return "\n".join(final_result)

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
