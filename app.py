import streamlit as st
import io
import re

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
            # טיפול חכם בשורות שבהן חסר ערך (Value)
            if '!' in line:
                # אם יש סימני קריאה, נחלץ את מה שביניהם כ-Footprint
                parts = line.split('!')
                pkg_id = parts[1].strip() if len(parts) > 1 else ""
                rest = parts[2].strip() if len(parts) > 2 else ""
                
                # ניקוי השארית (Value ו-Designator)
                rest_parts = rest.replace(';', ' ').split()
                val = rest_parts[0] if len(rest_parts) > 1 else ""
                des = rest_parts[-1] if len(rest_parts) > 0 else ""
            else:
                # אם אין סימני קריאה, נשתמש בהפרדה לפי רווחים/נקודה-פסיק
                temp_line = line.replace(';', ' ')
                parts = temp_line.split()
                if len(parts) >= 2:
                    pkg_id = parts[0]
                    des = parts[-1]
                    val = parts[1] if len(parts) > 2 else ""
                else:
                    continue

            # ניקוי שם האריזה (Footprint) לפי החוקים החדשים
            # 1. הסרת סוגריים ותוכנם
            pkg_id = re.sub(r'\(.*?\)', '', pkg_id)
            # 2. המרת נקודות ופסיקים לקו תחתון
            pkg_id = pkg_id.replace('.', '_').replace(',', '_')
            # 3. המרת אותיות לגדולות
            pkg_id = pkg_id.upper()
            
            # בניית השורה מחדש בצורה תקינה
            packages.append(f"!{pkg_id}! {val}; {des}")

        elif zone == "END":
            # המרת מקף לנקודה עבור פינים
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

# --- UI LAYOUT & ANIMATION ---
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
    if tab_titles:
        tabs = st.tabs(tab_titles)
        for idx, tab in enumerate(tabs):
            with tab:
                st.text_area(f"Preview: {processed_files_data[idx]['display_name']}", 
                             value=processed_files_data[idx]['content'], 
                             height=450, 
                             key=f"preview_text_{idx}")
