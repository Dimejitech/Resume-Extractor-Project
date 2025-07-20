import streamlit as st
import json
from app.file_reader import read_pdf, read_docx
from app.extractor import extract_resume_info
from app.extractor import generate_summary_hf

# Streamlit page config
st.set_page_config(page_title="📄 Resume Extractor", layout="centered")

def split_into_blocks(text):
    """
    Splits a section into blocks. A block ends when a completely empty line is found.
    """
    blocks = []
    current_block = []

    for line in text.splitlines():
        if line.strip() == "":
            if current_block:
                blocks.append("\n".join(current_block).strip())
                current_block = []
        else:
            current_block.append(line)

    if current_block:
        blocks.append("\n".join(current_block).strip())

    return blocks



# Title and description
st.title("📄 AI Resume Extractor")
st.markdown("Upload a resume in **PDF** or **DOCX** format to extract structured information like **Name**, **Email**, **Skills**, **Experience**, and **Education**.")

# File uploader
uploaded_file = st.file_uploader("**📎 Drag and drop your resume file here**", type=["pdf", "docx"])

if uploaded_file:
    file_type = uploaded_file.name.split(".")[-1].lower()

    try:
        # Read file based on type
        if file_type == "pdf":
            text = read_pdf(uploaded_file)
        elif file_type == "docx":
            text = read_docx(uploaded_file)
        else:
            st.error("Unsupported file format.")
            text = ""

        # Extract and display results
        if text:
            st.success("✅ Resume loaded and processed successfully!")
            extracted_data = extract_resume_info(text)

            st.markdown("---")
            st.header("📋 Extracted Resume Details")

            for section, content in extracted_data.items():
                st.subheader(f"🔹 {section}")

                # If content is a long block of text (like Experience, Projects), show as expandable blocks
                if section.lower() == "experience":
                    if isinstance(content, list):
                        for i, exp in enumerate(content):
                            title = exp.get("title_or_role", f"Experience {i+1}")
                            with st.expander(title):
                                st.markdown(f"**Date:** {exp.get('date_range', 'N/A')}")
                                responsibilities = exp.get("responsibilities", [])
                                if responsibilities:
                                    for r in responsibilities:
                                        st.markdown(f"- {r}")
                                else:
                                    st.markdown("_No responsibilities listed_")
                    else:
                        st.markdown("_No structured experience data found_")

                elif section.lower() == "projects":
                    if isinstance(content, list):
                        for i, project in enumerate(content):
                            title = project.get("title", f"Project {i+1}")
                            with st.expander(title):
                                details = project.get("details", [])
                                for detail in details:
                                    st.markdown(f"- {detail}")
                    else:
                        st.markdown("_No structured project data found_")

                elif section.lower() == "extracurriculars":
                    if isinstance(content, str):
                        blocks = split_into_blocks(content)
                        if blocks:
                            for i, block in enumerate(blocks):
                                title = block.split("\n")[0]
                                with st.expander(title if title else f"{section} {i+1}"):
                                    st.markdown(block)
                        else:
                            st.markdown("_No entries found_")
                    else:
                        st.markdown("_Invalid format for section_")
    

                # If it's a simple list (like skills or certifications)
                elif isinstance(content, list):
                    if content:
                        for item in content:
                            st.markdown(f"- {item}")
                    else:
                        st.markdown("_No data found_")

                # If it's a single string (like Name, Email, LinkedIn, etc.)
                else:
                    st.markdown(content if content else "_Not found_")

            st.markdown("---")
            st.header("🧠 AI-Generated Resume Summary")

            with st.spinner("Generating professional summary..."):
                summary = generate_summary_hf(extracted_data)

            if summary.startswith("⚠️"):
                st.warning(summary)
            else:
                st.success("Summary generated!")
                st.markdown(summary)

            st.markdown("---")
            st.header("📤 Export Extracted Data")

                # JSON Export
            json_data = json.dumps(extracted_data, indent=2)
            st.download_button(
                label="📥 Download Resume Data (JSON)",
                data=json_data,
                file_name="resume_data.json",
                mime="application/json"
            )

            # CSV Export
            import pandas as pd
            from io import StringIO

            flat_data = []

            if "Skills" in extracted_data and isinstance(extracted_data["Skills"], list):
                for skill in extracted_data["Skills"]:
                    flat_data.append({"Section": "Skill", "Content": skill})
            if "Experience" in extracted_data and isinstance(extracted_data["Experience"], str):
                for block in extracted_data["Experience"].split("\n\n"):
                    flat_data.append({"Section": "Experience", "Content": block.strip()})

            if flat_data:
                df = pd.DataFrame(flat_data)
                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)

                st.download_button(
                    label="📥 Download Structured Data (CSV)",
                    data=csv_buffer.getvalue(),
                    file_name="resume_data.csv",
                    mime="text/csv"
                )
            else:
                st.info("No structured data found for CSV export.")
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")

        
