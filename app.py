import streamlit as st
import io

# --- CORE LOGIC ---
def process_single_file(uploaded_file):
    content = uploaded_file.getvalue().decode('cp1255', errors='ignore')
    lines = content.splitlines()
    zone = None
    packages = []
    nets_data = {}
    current_net = None

    for line in lines:
        raw_line = line 
        line = line.strip()
        if not line: continue
            
        upper_line = line.upper()
        if any(k in upper_line for k in ["PART", "PACKAGES", "$PACKAGES"]):
            zone = "START"
            continue
        elif any(k in upper_line for k in ["$NETS", "NET"]):
            zone = "END"
            continue
        elif upper_line.startswith('$'):
            zone = None
            continue

        if zone == "START":
            temp_line = line.replace('!', ' ').replace(';', ' ')
            parts = temp_line.split()
            if len(parts) >= 2:
                # Replace dots with underscores in Footprint name
                pkg_id = parts[0].replace('.', '_')
                des = parts[-1]
                if len(parts) > 2:
                    val = parts[1]
                    packages.append(f"!{pkg_id}! {val}; {des}")
                else:
                    # Empty value column with semicolon
                    packages.append(f"!{pkg_id}! ; {des}")

        elif zone == "END":
            # Convert dash to dot for pins (e.g., U46-C22 -> U46.C22)
            processed_line = line.replace('-', '.')
            clean_line = processed_line.replace(',', ' ').replace(';', ' ').replace('*', ' ')
            parts = clean_line.split()
            if not parts: continue
            
            if not raw_line.startswith((' ', '\t', '*')):
                current_net = parts[0]
                if current_net not in nets_data:
                    nets_data[current_net] = []
                nets_data[current_net].extend(parts[1:])
            else:
                if current_net:
                    nets_data[current_net].extend(parts)

    final_output = ["$PACKAGES"]
    final_output.extend(packages)
    final_output.append("$NETS")
    for net_name, pins in nets_data.items():
        actual_pins = [p.strip() for p in pins if p.strip() and p.strip() != ';']
        if not actual_pins: continue
        for i in range(0, len(actual_pins), 10):
            chunk = actual_pins[i:i+10]
            final_output.append(f"{net_name}; {' '.join(chunk)}")
    
    final_output.append("$End")
    return "\n".join(final_output)

# --- UI LAYOUT ---
st.set_page_config(page_title="Mind-Board Converter", layout="wide")

logo_url = "https://raw.githubusercontent.com/yurko120/netlist-converter/main/.devcontainer/MindBoard-Logo.jpg"

st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("{logo_url}");
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center 70%; 
        background-size: 45%; 
    }}
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(255, 255, 255, 0.92); 
        z-index: -1;
    }}
    .centered-title {{
        text-align: center;
        color: #000000;
        font-size: 2.8em !important; 
        font-weight: 900 !important; 
        margin-bottom: 20px !important;
    }}
    [data-testid="stTextInput"] label {{
        font-size: 1rem !important; 
        font-weight: 700 !important; 
        color: #000000 !important;
        padding-bottom: 8px !important;
    }}
    .stTextArea textarea {{
        background-color: rgba(255, 255, 255, 0.6) !important; 
        border: 2px solid #000000 !important;
        font-family: 'Courier New', monospace;
        font-weight: 800 !important; 
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
                custom_name = st.text_input("Enter Output Name:", 
                                            value=f"{original_name}_transformed", 
                                            key=f"name_input_{idx}")
                content = process_single_file(f)
                processed_files_data.append({"display_name": custom_name, "content": content})
                full_filename = custom_name if custom_name.endswith(('.txt', '.net')) else f"{custom_name}.txt"
                st.download_button(
                    label=f"📥 Download {full_filename}",
                    data=content,
                    file_name=full_filename,
                    mime="text/plain",
                    key=f"dl_btn_{idx}",
                    use_container_width=True
                )
                st.markdown("<br>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🔍 Technical Preview (Per File)")
    tab_titles = [item["display_name"] for item in processed_files_data]
    tabs = st.tabs(tab_titles)
    for idx, tab in enumerate(tabs):
        with tab:
            st.text_area(f"Preview: {processed_files_data[idx]['display_name']}", 
                         value=processed_files_data[idx]['content'], 
                         height=450, 
                         key=f"preview_text_{idx}")
