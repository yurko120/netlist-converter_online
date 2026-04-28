import streamlit as st
import io
import re

# --- CORE LOGIC: Precise Package Name Cleaning ---
def clean_package_name(name):
    if not name:
        return ""
    
    # Define ONLY the illegal characters you mentioned
    illegal_chars = r"[#@*+=%^&/]"
    
    # 1. Handle illegal chars at the very END of the name (Delete them)
    # We check if the last character is in our illegal list
    while name and re.match(illegal_chars, name[-1]):
        name = name[:-1]
    
    # 2. Handle illegal chars in the MIDDLE (Replace with underscore)
    cleaned = re.sub(illegal_chars, '_', name)
    
    # 3. Clean double underscores if any were created
    cleaned = re.sub(r'_+', '_', cleaned)
    
    return cleaned.upper()

def process_single_file(uploaded_file):
    raw_bytes = uploaded_file.getvalue()
    try:
        content = raw_bytes.decode('cp1255', errors='ignore')
    except:
        content = raw_bytes.decode('utf-8', errors='ignore')

    content = content.replace('\r\n', '\n').replace('\r', '\n')
    content = content.replace('\xa0', ' ').replace('\t', ' ')
    
    lines = content.split('\n')
    zone = None
    packages = []
    nets_data = {}
    current_net = None
    
    for line in lines:
        raw_line = line
        stripped_line = line.strip()
        if not stripped_line:
            continue
            
        upper_line = stripped_line.upper()

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
            # Remove parentheses content
            clean_step = re.sub(r'\(.*?\)', '', stripped_line)
            clean_step = clean_step.replace('!', ' ').replace(';', ' ')
            parts = clean_step.split()
            
            if len(parts) >= 2:
                pkg_raw = parts[0]
                # Apply the specific cleaning logic
                pkg_id = clean_package_name(pkg_raw)
                
                des = parts[-1]
                val = parts[1] if len(parts) > 2 else ""
                packages.append(f"!{pkg_id}! {val}; {des}")

        # 2. PROCESS NETS
        elif zone == "END":
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

    output = ["$PACKAGES"]
    output.extend(packages)
    output.append("$NETS")
    for net_name, pins in nets_data.items():
        clean_pins = []
        for p in pins:
            p_f = p.strip()
            if p_f and p_f not in clean_pins:
                clean_pins.append(p_f)
        if clean_pins:
            output.append(f"{net_name}; {' '.join(clean_pins)}")
            
    output.append("$End")
    return "\n".join(output)

# --- STREAMLIT UI: Keeping the requested style ---
st.set_page_config(page_title="Mind-Board Converter", layout="wide")
logo_url = "https://raw.githubusercontent.com/yurko120/netlist-converter/main/.devcontainer/MindBoard-Logo.jpg"

st.markdown(f"""
    <style>
    @keyframes fadeInDown {{
        0% {{ opacity: 0; transform: translateY(-30px); }}
        100% {{ opacity: 1; transform: translateY(0); }}
    }}
    .stApp {{
        background-image: url("{logo_url}");
        background-repeat: no-repeat; background-attachment: fixed;
        background-position: center 70%; background-size: 45%; 
    }}
    .stApp::before {{
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(255, 255, 255, 0.93); z-index: -1;
    }}
    .centered-title {{
        text-align: center; color: #000000; font-size: 3.5em !important; 
        font-weight: 900 !important; margin-bottom: 30px !important;
        animation: fadeInDown 0.8s ease-out;
    }}
    .bold-header {{
        font-weight: 900 !important; color: #000000 !important;
        font-size: 1.6em !important; margin-bottom: 15px !important;
    }}
    .stTextArea textarea {{
        background-color: rgba(255, 255, 255, 0.8) !important; 
        border: 2px solid #000000 !important;
        font-family: 'Courier New', monospace; font-weight: 700 !important;
        color: #000000 !important;
    }}
    p, span, label, .stMarkdown {{
        font-weight: 800 !important; color: #000000 !important;
    }}
    </style>
    <h1 class="centered-title">Mind-Board Converter</h1>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown('<p class="bold-header">1. Upload Source Files</p>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Upload .NET files", accept_multiple_files=True, label_visibility="collapsed")

if uploaded_files:
    results = []
    with col2:
        st.markdown('<p class="bold-header">2. File Settings & Download</p>', unsafe_allow_html=True)
        for idx, f in enumerate(uploaded_files):
            with st.container():
                st.markdown(f"**Current File:** `{f.name}`")
                original_name = f.name.rsplit('.', 1)[0]
                custom_name = st.text_input("New Output Name:", value=f"{original_name}_fixed", key=f"in_{idx}")
                full_name = f"{custom_name}.txt" if not custom_name.endswith(('.txt', '.net')) else custom_name
                content = process_single_file(f)
                results.append({"name": full_name, "content": content})
                st.download_button(label=f"📥 Download {full_name}", data=content, file_name=full_name, mime="text/plain", key=f"btn_{idx}", use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)

    st.divider()
    st.markdown('<h2 style="text-align:left; font-weight:900;">🔍 Technical Preview</h2>', unsafe_allow_html=True)
    if results:
        tabs = st.tabs([r["name"] for r in results])
        for idx, tab in enumerate(tabs):
            with tab:
                st.text_area("Live Output Preview:", value=results[idx]["content"], height=500, key=f"txt_{idx}")
