import streamlit as st
import io
import re

# --- CORE LOGIC: Netlist Transformation ---
def process_single_file(uploaded_file):
    # Forced decoding with handling for all types of line breaks
    raw_bytes = uploaded_file.getvalue()
    try:
        content = raw_bytes.decode('cp1255', errors='ignore')
    except:
        content = raw_bytes.decode('utf-8', errors='ignore')

    # STEP 1: Normalize all whitespace and line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    content = content.replace('\xa0', ' ').replace('\t', ' ')
    
    lines = content.split('\n')
    zone = None
    packages = []
    nets_data = {}
    current_net = None
    
    forbidden_chars = r"[/\\*#@&^%?]"

    for line in lines:
        # We need the leading whitespace info, so we use raw_line for detection
        # but stripped_line for content extraction
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
            # Clean up the package line
            clean = re.sub(r'\(.*?\)', '', stripped_line)
            clean = re.sub(forbidden_chars, "", clean)
            clean = clean.replace('!', ' ').replace(';', ' ')
            parts = clean.split()
            
            if len(parts) >= 2:
                pkg_id = parts[0].replace('.', '_').replace(',', '_').upper()
                des = parts[-1]
                val = parts[1] if len(parts) > 2 else ""
                packages.append(f"!{pkg_id}! {val}; {des}")

        # 2. PROCESS NETS (State Machine Logic)
        elif zone == "END":
            # If the line starts with NO whitespace, it's a NEW Net
            if len(raw_line) > 0 and not raw_line[0].isspace():
                # Clean delimiters and split
                clean = stripped_line.replace(';', ' ').replace(',', ' ')
                parts = clean.split()
                if parts:
                    current_net = parts[0]
                    if current_net not in nets_data:
                        nets_data[current_net] = []
                    # Add remaining pins on the same line
                    for p in parts[1:]:
                        nets_data[current_net].append(p.replace('-', '.'))
            
            # If the line STARTS with whitespace, it's a continuation
            else:
                if current_net:
                    clean = stripped_line.replace(';', ' ').replace(',', ' ')
                    parts = clean.split()
                    for p in parts:
                        nets_data[current_net].append(p.replace('-', '.'))

    # --- BUILDING THE FINAL TEXT ---
    output = ["$PACKAGES"]
    output.extend(packages)
    output.append("$NETS")
    
    for net_name, pins in nets_data.items():
        # Remove duplicates and empty strings
        clean_pins = []
        for p in pins:
            p_fixed = p.strip()
            if p_fixed and p_fixed not in clean_pins:
                clean_pins.append(p_fixed)
        
        if clean_pins:
            output.append(f"{net_name}; {' '.join(clean_pins)}")
            
    output.append("$End")
    return "\n".join(output)

# --- STREAMLIT UI ---
st.set_page_config(page_title="Netlist Converter", layout="wide")

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
        background-color: rgba(255, 255, 255, 0.95); z-index: -1;
    }}
    .title-text {{
        text-align: center; color: black; font-size: 3em; font-weight: bold;
    }}
    </style>
    <h1 class="title-text">Mind-Board Converter</h1>
    """, unsafe_allow_html=True)

files = st.file_uploader("Upload .NET Files", accept_multiple_files=True)

if files:
    for i, f in enumerate(files):
        st.subheader(f"File: {f.name}")
        
        # User defined output name
        base_name = f.name.rsplit('.', 1)[0]
        out_name = st.text_input("Save as:", value=f"{base_name}_fixed", key=f"input_{i}")
        
        # Transformation
        result = process_single_file(f)
        
        # Buttons and Preview
        st.download_button("Download Result", result, file_name=f"{out_name}.txt", key=f"btn_{i}")
        st.text_area("Live Preview", result, height=300, key=f"area_{i}")
