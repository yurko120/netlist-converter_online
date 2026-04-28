import streamlit as st
import io
import re

# --- CORE LOGIC: Netlist Transformation ---
def process_single_file(uploaded_file):
    # Handling file encoding and cleaning invisible characters
    try:
        content = uploaded_file.getvalue().decode('cp1255', errors='ignore')
    except:
        content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
    
    # Replacing non-breaking spaces and tabs with standard spaces
    content = content.replace('\xa0', ' ').replace('\t', ' ')
    lines = content.splitlines()
    
    zone = None
    packages = []
    nets_data = {}
    current_net = None
    
    # Characters strictly forbidden in Footprint names
    forbidden_chars = r"[/\\*#@&^%?]"

    for line in lines:
        line_strip = line.strip()
        if not line_strip: continue
        
        # Detect Section Transitions
        upper_line = line_strip.upper()
        if "$PACKAGES" in upper_line or "PART" in upper_line:
            zone = "START"
            continue
        elif "$NETS" in upper_line or "NET" in upper_line:
            zone = "END"
            continue
        elif line_strip.startswith('$'):
            zone = None
            continue

        # 1. PROCESS PACKAGES (Footprints)
        if zone == "START":
            # Remove parentheses and forbidden characters
            clean_pkg = re.sub(r'\(.*?\)', '', line_strip)
            clean_pkg = re.sub(forbidden_chars, "", clean_pkg)
            clean_pkg = clean_pkg.replace('!', ' ').replace(';', ' ')
            
            parts = clean_pkg.split()
            if len(parts) >= 2:
                # Expected format: !FOOTPRINT! VALUE; DESIGNATOR
                pkg_id = parts[0].replace('.', '_').replace(',', '_').upper()
                des = parts[-1]
                val = parts[1] if len(parts) > 2 else ""
                packages.append(f"!{pkg_id}! {val}; {des}")

        # 2. PROCESS NETS (Logic tuned for S0BMDL02_R00.NET)
        elif zone == "END":
            # A Net name is identified by a word ending with a semicolon (e.g., NetQ10_E;)
            net_match = re.match(r'^\s*([^;\s]+);', line)
            
            if net_match:
                # Found a new Net declaration
                current_net = net_match.group(1).strip()
                if current_net not in nets_data:
                    nets_data[current_net] = []
                
                # Extract any pins following the semicolon on the same line
                remaining_text = line[net_match.end():]
                pins = remaining_text.replace(',', ' ').replace('-', '.').split()
                nets_data[current_net].extend(pins)
            
            elif current_net:
                # This is a continuation line (indented or following a comma)
                pins = line_strip.replace(',', ' ').replace('-', '.').split()
                nets_data[current_net].extend(pins)

    # --- BUILDING THE FINAL OUTPUT ---
    final_result = ["$PACKAGES"]
    final_result.extend(packages)
    final_result.append("$NETS")
    
    for net_name, pins in nets_data.items():
        # Clean up pin names and remove stray characters
        clean_pins = [p.strip().strip(';') for p in pins if p.strip() and p.strip() != ',']
        if clean_pins:
            # Allegro Standard Format: NetName; Pin1 Pin2 Pin3...
            final_result.append(f"{net_name}; {' '.join(clean_pins)}")
    
    final_result.append("$End")
    return "\n".join(final_result)

# --- STREAMLIT UI CONFIGURATION ---
st.set_page_config(page_title="Netlist Converter Tool", layout="wide")

# Background and visual styling
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
    .stTextArea textarea {{
        font-family: 'Courier New', monospace;
    }}
    </style>
    <h1 class="main-title">Mind-Board Converter</h1>
    """, unsafe_allow_html=True)

# File upload section
uploaded_files = st.file_uploader("Upload Source .NET Files", accept_multiple_files=True)

if uploaded_files:
    for idx, f in enumerate(uploaded_files):
        st.write(f"--- Processing: {f.name} ---")
        
        # File naming logic
        original_name = f.name.rsplit('.', 1)[0]
        output_filename = st.text_input(f"Output name for {f.name}:", 
                                       value=f"{original_name}_fixed", 
                                       key=f"name_{idx}")
        
        # Process the file content
        transformed_content = process_single_file(f)
        
        # Action buttons
        st.download_button(
            label=f"Download {output_filename}.txt",
            data=transformed_content,
            file_name=f"{output_filename}.txt",
            mime="text/plain",
            key=f"dl_{idx}"
        )
        
        # Preview area
        st.text_area("File Preview", transformed_content, height=350, key=f"preview_{idx}")
