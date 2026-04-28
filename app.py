import streamlit as st
import io
import re

# --- CORE LOGIC: Netlist Transformation ---
def process_single_file(uploaded_file):
    # Load file and handle non-breaking spaces (\xa0) and tabs
    try:
        content = uploaded_file.getvalue().decode('cp1255', errors='ignore')
    except Exception:
        content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
        
    content = content.replace('\xa0', ' ').replace('\t', ' ')
    
    lines = content.splitlines()
    zone = None
    packages = []
    nets_data = {}
    current_net = None
    
    # Characters forbidden in footprint names
    forbidden_chars = r"[/\\*#@&^%?]"

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

        # 1. PACKAGES SECTION (Footprints)
        if zone == "START":
            # Sanitize footprint: remove parentheses and forbidden characters
            mod_line = re.sub(r'\(.*?\)', '', line_strip)
            mod_line = re.sub(forbidden_chars, "", mod_line)
            mod_line = mod_line.replace('!', ' ').replace(';', ' ')
            parts = mod_line.split()
            
            if len(parts) >= 2:
                # Format: !FOOTPRINT! VALUE; DESIGNATOR
                pkg_id = parts[0].replace('.', '_').replace(',', '_').upper()
                des = parts[-1]
                val = parts[1] if len(parts) > 2 else ""
                if len(pkg_id) >= 2:
                    packages.append(f"!{pkg_id}! {val}; {des}")

        # 2. NETS SECTION (Connections)
        elif zone == "END":
            # If line doesn't start with space, it's a new Net name
            if not raw_line.startswith((' ', '\t')):
                clean_line = line_strip.replace(',', ' ').replace(';', ' ')
                parts = clean_line.split()
                if parts:
                    current_net = parts[0]
                    if current_net not in nets_data:
                        nets_data[current_net] = []
                    # Add pins from the same line, replacing - with .
                    for p in parts[1:]:
                        nets_data[current_net].append(p.replace('-', '.'))
            
            # If line starts with space, it's a continuation
            else:
                if current_net:
                    clean_line = line_strip.replace(',', ' ').replace(';', ' ')
                    parts = clean_line.split()
                    for p in parts:
                        nets_data[current_net].append(p.replace('-', '.'))

    # --- BUILDING OUTPUT ---
    final_result = ["$PACKAGES"]
    final_result.extend(packages)
    final_result.append("$NETS")
    
    for net_name, pins in nets_data.items():
        actual_pins = []
        for p in pins:
            p_clean = p.strip().strip(';')
            if p_clean:
                actual_pins.append(p_clean)
        
        if actual_pins:
            # Standard Format: NetName; Pin1 Pin2...
            final_result.append(f"{net_name}; {' '.join(actual_pins)}")
    
    final_result.append("$End")
    return "\n".join(final_result)

# --- STREAMLIT UI ---
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
                
                # Logic for filename generation
                original_name = f.name.rsplit('.', 1)[0]
                default_name = f"{original_name}_transformed"
                
                custom_name = st.text_input("Enter Output Name:", 
                                            value=default_name, 
                                            key=f"name_input_{idx}")
                
                # Ensure filename has an extension
                if not custom_name.endswith(('.txt', '.net')):
                    full_filename = f"{custom_name}.txt"
                else:
                    full_filename = custom_name
                
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
