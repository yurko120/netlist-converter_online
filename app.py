import streamlit as st
import io
import re

# --- CORE LOGIC: Netlist Transformation (Ensuring no missing data) ---
def process_single_file(uploaded_file):
    raw_bytes = uploaded_file.getvalue()
    try:
        content = raw_bytes.decode('cp1255', errors='ignore')
    except:
        content = raw_bytes.decode('utf-8', errors='ignore')

    # Normalize line endings and whitespace
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    content = content.replace('\xa0', ' ').replace('\t', ' ')
    
    lines = content.split('\n')
    zone = None
    packages = []
    nets_data = {}
    current_net = None
    
    forbidden_chars = r"[/\\*#@&^%?]"

    for line in lines:
        raw_line = line
        stripped_line = line.strip()
        if not stripped_line:
            continue
            
        upper_line = stripped_line.upper()

        # Section Detection
        if "$PACKAGES" in upper_line:
            zone = "START"
            continue
        elif "$NETS" in upper_line:
            zone = "END"
            continue
        elif stripped_line.startswith('$') and zone is not None:
            zone = None
            continue

        # 1. PROCESS PACKAGES
        if zone == "START":
            clean = re.sub(r'\(.*?\)', '', stripped_line)
            clean = re.sub(forbidden_chars, "", clean)
            clean = clean.replace('!', ' ').replace(';', ' ')
            parts = clean.split()
            if len(parts) >= 2:
                pkg_id = parts[0].replace('.', '_').replace(',', '_').upper()
                des = parts[-1]
                val = parts[1] if len(parts) > 2 else ""
                packages.append(f"!{pkg_id}! {val}; {des}")

        # 2. PROCESS NETS
        elif zone == "END":
            # If line starts at index 0 with no space, it's a new Net name
            if len(raw_line) > 0 and not raw_line[0].isspace():
                clean = stripped_line.replace(';', ' ').replace(',', ' ')
                parts = clean.split()
                if parts:
                    current_net = parts[0]
                    if current_net not in nets_data:
                        nets_data[current_net] = []
                    for p in parts[1:]:
                        nets_data[current_net].append(p.replace('-', '.'))
            else:
                if current_net:
                    clean = stripped_line.replace(';', ' ').replace(',', ' ')
                    parts = clean.split()
                    for p in parts:
                        nets_data[current_net].append(p.replace('-', '.'))

    # --- BUILDING OUTPUT ---
    output = ["$PACKAGES"]
    output.extend(packages)
    output.append("$NETS")
    for net_name, pins in nets_data.items():
        clean_pins = []
        for p in pins:
            p_fixed = p.strip()
            if p_fixed and p_fixed not in clean_pins:
                clean_pins.append(p_fixed)
        if clean_pins:
            output.append(f"{net_name}; {' '.join(clean_pins)}")
            
    output.append("$End")
    return "\n".join(output)

# --- STREAMLIT UI: Full Visual Style ---
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
        text-align: center; color: #000000; font-size: 3em !important; 
        font-weight: 900 !important; margin-bottom: 30px !important;
    }}
    .stTextArea textarea {{
        background-color: rgba(255, 255, 255, 0.6) !important; 
        border: 2px solid #000000 !important;
        font-family: 'Courier New', monospace; font-weight: 800 !important; 
    }}
    </style>
    <h1 class="centered-title">Mind-Board Converter</h1>
    """, unsafe_allow_html=True)

# Layout setup: Two Columns
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
                
                # Filename logic
                original_name = f.name.rsplit('.', 1)[0]
                default_name = f"{original_name}_transformed"
                
                custom_name = st.text_input("Enter Output Name:", 
                                            value=default_name, 
                                            key=f"name_input_{idx}")
                
                full_filename = f"{custom_name}.txt" if not custom_name.endswith(('.txt', '.net')) else custom_name
                
                content = process_single_file(f)
                processed_files_data.append({"display_name": full_filename, "content": content})
                
                st.download_button(
                    label=f"Download {full_filename}", 
                    data=content, 
                    file_name=full_filename, 
                    mime="text/plain", 
                    key=f"dl_btn_{idx}", 
                    use_container_width=True
                )
                st.markdown("<br>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🔍 Technical Preview")
    tab_titles = [item["display_name"] for item in processed_files_data]
    if tab_titles:
        tabs = st.tabs(tab_titles)
        for idx, tab in enumerate(tabs):
            with tab:
                st.text_area(f"Preview: {processed_files_data[idx]['display_name']}", 
                             value=processed_files_data[idx]['content'], 
                             height=450, 
                             key=f"preview_text_{idx}")
