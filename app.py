import streamlit as st
import io
import re

# --- CORE LOGIC: Safe Transformation ---
def process_single_file(uploaded_file):
    content = uploaded_file.getvalue().decode('cp1255', errors='ignore')
    lines = content.splitlines()
    zone = None
    final_output = []
    
    # Special characters to remove globally: / * \ # @ & ^ % ?
    chars_to_remove = r"[/\\*#@&^%?]"

    for line in lines:
        raw_line = line
        strip_line = line.strip()
        if not strip_line:
            final_output.append("")
            continue
            
        upper_line = strip_line.upper()
        
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

        # 1. FOOTPRINTS SECTION (Packages)
        if zone == "START":
            # Remove parentheses and their content
            mod_line = re.sub(r'\(.*?\)', '', raw_line)
            # Remove forbidden special characters
            mod_line = re.sub(chars_to_remove, "", mod_line)
            
            # Handle the Footprint name specifically (between ! or at start)
            if '!' in mod_line:
                parts = mod_line.split('!')
                if len(parts) >= 3:
                    # Sanitize the footprint part
                    pkg = parts[1].replace('.', '_').replace(',', '_').upper()
                    # Reconstruct the line
                    mod_line = f"!{pkg}!{parts[2]}"
            
            final_output.append(mod_line)

        # 2. NETS SECTION (Preserve names like GND, E, B, H4)
        elif zone == "END":
            # ONLY replace '-' with '.' to separate component and pin
            # NO other characters are removed to ensure no data is lost
            mod_line = raw_line.replace('-', '.')
            final_output.append(mod_line)
        
        else:
            final_output.append(raw_line)

    return "\n".join(final_output)

# --- UI LAYOUT & STYLING ---
st.set_page_config(page_title="Mind-Board Converter", layout="wide")

logo_url = "https://raw.githubusercontent.com/yurko120/netlist-converter/main/.devcontainer/MindBoard-Logo.jpg"

st.markdown(f"""
    <style>
    @keyframes slideInFromTop {{
        0% {{ transform: translateY(-50px); opacity: 0; }}
        60% {{ transform: translateY(10px); opacity: 1; }}
        100% {{ transform: translateY(0); opacity: 1; }}
    }}
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
        animation: slideInFromTop 1.2s ease-out;
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
