import streamlit as st
import io
import re

# --- CORE LOGIC: Netlist Transformation ---
def process_single_file(uploaded_file):
    # Load content and clean non-breaking spaces (\xa0)
    try:
        content = uploaded_file.getvalue().decode('cp1255', errors='ignore')
    except:
        content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
    
    content = content.replace('\xa0', ' ').replace('\t', ' ')
    lines = content.splitlines()
    
    zone = None
    packages = []
    nets_data = {}
    current_net = None
    
    forbidden_chars = r"[/\\*#@&^%?]"

    for line in lines:
        raw_line = line
        line_strip = line.strip()
        if not line_strip: continue
        
        upper_line = line_strip.upper()
        
        # Section Detection
        if "$PACKAGES" in upper_line or "PART" in upper_line:
            zone = "START"
            continue
        elif "$NETS" in upper_line or "NET" in upper_line:
            zone = "END"
            continue
        elif line_strip.startswith('$'):
            zone = None
            continue

        # 1. PROCESS PACKAGES
        if zone == "START":
            clean_pkg = re.sub(r'\(.*?\)', '', line_strip)
            clean_pkg = re.sub(forbidden_chars, "", clean_pkg)
            clean_pkg = clean_pkg.replace('!', ' ').replace(';', ' ')
            
            parts = clean_pkg.split()
            if len(parts) >= 2:
                pkg_id = parts[0].replace('.', '_').replace(',', '_').upper()
                des = parts[-1]
                val = parts[1] if len(parts) > 2 else ""
                packages.append(f"!{pkg_id}! {val}; {des}")

        # 2. PROCESS NETS (Updated for S0BMDL02_R00.NET format)
        elif zone == "END":
            # If the line starts with a non-space character, it's a NEW Net
            if not raw_line.startswith((' ', '\t')):
                # Split by semicolon or space to get the Net Name
                clean_line = line_strip.replace(';', ' ').replace(',', ' ')
                parts = clean_line.split()
                if parts:
                    current_net = parts[0]
                    if current_net not in nets_data:
                        nets_data[current_net] = []
                    # Add any pins found on the same line
                    for p in parts[1:]:
                        nets_data[current_net].append(p.replace('-', '.'))
            
            # If the line starts with a space, it's a continuation of the current Net
            else:
                if current_net:
                    clean_line = line_strip.replace(';', ' ').replace(',', ' ')
                    parts = clean_line.split()
                    for p in parts:
                        nets_data[current_net].append(p.replace('-', '.'))

    # --- BUILDING OUTPUT ---
    final_result = ["$PACKAGES"]
    final_result.extend(packages)
    final_result.append("$NETS")
    
    for net_name, pins in nets_data.items():
        # Clean pin names and remove empty entries
        clean_pins = [p.strip() for p in pins if p.strip() and p.strip() != ',']
        if clean_pins:
            # Allegro Standard Format: NetName; Pin1 Pin2 Pin3...
            final_result.append(f"{net_name}; {' '.join(clean_pins)}")
    
    final_result.append("$End")
    return "\n".join(final_result)

# --- STREAMLIT UI ---
st.set_page_config(page_title="Netlist Converter Tool", layout="wide")

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
    .main-title {{
        text-align: center; color: #000000; font-size: 3em !important; font-weight: 900;
        margin-bottom: 30px;
    }}
    </style>
    <h1 class="main-title">Mind-Board Converter</h1>
    """, unsafe_allow_html=True)

uploaded_files = st.file_uploader("Upload Source .NET Files", accept_multiple_files=True)

if uploaded_files:
    for idx, f in enumerate(uploaded_files):
        st.write(f"--- Processing: {f.name} ---")
        original_name = f.name.rsplit('.', 1)[0]
        output_filename = st.text_input(f"Output name for {f.name}:", 
                                       value=f"{original_name}_fixed", 
                                       key=f"name_{idx}")
        
        transformed_content = process_single_file(f)
        
        st.download_button(
            label=f"Download {output_filename}.txt",
            data=transformed_content,
            file_name=f"{output_filename}.txt",
            mime="text/plain",
            key=f"dl_{idx}"
        )
        st.text_area("File Preview", transformed_content, height=350, key=f"preview_{idx}")
