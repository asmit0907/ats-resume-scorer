import streamlit as st
import os
import io
import pandas as pd
from parser import extract_text
from ai_service import GeminiResumeService, GroqResumeService
from exporter import export_to_docx, export_to_pdf

# Set page config
st.set_page_config(
    page_title="ResumeAI - ATS Scorer & Tailor",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium design (Professional Blue Light Theme)
st.markdown("""
<style>
    /* Headings styling */
    h1, h2, h3, h4, h5, h6 {
        color: #0F172A !important;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    
    /* Header Banner styling */
    .header-banner {
        background: linear-gradient(135deg, #2563EB 0%, #06B6D4 100%);
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.08);
    }
    .header-banner h1 {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 800;
        margin: 0;
        font-size: 2.5rem;
        color: white !important;
    }
    .header-banner p {
        font-size: 1.05rem;
        opacity: 0.95;
        margin-top: 8px;
        margin-bottom: 0;
        color: rgba(255, 255, 255, 0.9) !important;
    }

    /* Cards styling */
    .card-container {
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
        margin-bottom: 20px;
    }
    .metric-card {
        flex: 1;
        min-width: 180px;
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.02);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(37, 99, 235, 0.05);
        border-color: #CBD5E1;
    }
    .metric-value {
        font-size: 2.1rem;
        font-weight: 800;
        margin-bottom: 2px;
    }
    .metric-label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #475569;
        opacity: 0.85;
    }
    
    /* Dynamic border/text colors based on rating */
    .score-green { color: #22C55E !important; border-top: 4px solid #22C55E; }
    .score-yellow { color: #F59E0B !important; border-top: 4px solid #F59E0B; }
    .score-red { color: #EF4444 !important; border-top: 4px solid #EF4444; }
    
    /* Checklist styles */
    .check-item {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
        font-size: 1rem;
    }
    .check-pass { color: #22C55E; margin-right: 10px; font-weight: bold; }
    .check-fail { color: #EF4444; margin-right: 10px; font-weight: bold; }
    
    /* Info banners */
    .info-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #2563EB;
        color: #475569;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 15px;
        font-size: 0.95rem;
        line-height: 1.5;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.01);
    }
</style>
""", unsafe_allow_html=True)

# App Title & Header Banner
st.markdown("""
<div class="header-banner">
    <h1>ResumeAI ATS Scorer & Optimiser</h1>
    <p>Upload your resume, paste the target job description, and get instant ATS compatibility scores, gap analysis, and a tailor-made resume!</p>
</div>
""", unsafe_allow_html=True)

# Sidebar setup
st.sidebar.image("https://img.icons8.com/color/96/resume.png", width=80)
st.sidebar.title("Configuration")

# Provider Selection
provider = st.sidebar.selectbox("AI Provider", options=["Google Gemini", "Groq"], index=0)

# API Key and Model handling based on Provider
if provider == "Google Gemini":
    env_api_key = os.environ.get("GEMINI_API_KEY")
    if not env_api_key:
        try:
            if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                env_api_key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            pass

    if env_api_key:
        api_key = env_api_key
        st.sidebar.success("🔑 Gemini API Key configured on server.")
    else:
        api_key = st.sidebar.text_input("Gemini API Key", type="password", 
                                       help="Get an API key from Google AI Studio. The key is processed locally and never stored.")
    
    model_selection = st.sidebar.selectbox("Gemini Model Version", 
                                          options=["gemini-2.5-flash", "gemini-2.5-pro"],
                                          index=0,
                                          help="Flash is extremely fast, while Pro offers deeper reasoning and higher quality rewriting.")
else:
    env_api_key = os.environ.get("GROQ_API_KEY")
    if not env_api_key:
        try:
            if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                env_api_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass

    if env_api_key:
        api_key = env_api_key
        st.sidebar.success("🔑 Groq API Key configured on server.")
    else:
        api_key = st.sidebar.text_input("Groq API Key", type="password", 
                                       help="Get an API key from Groq Console. The key is processed locally and never stored.")
    
    model_selection = st.sidebar.selectbox("Groq Model Version", 
                                          options=["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
                                          index=0,
                                          help="Llama-3.3-70b is highly recommended for complex parsing and rewriting tasks.")

st.sidebar.markdown("---")
target_role = st.sidebar.text_input("Target Job Title / Position", placeholder="e.g. Senior Fullstack Engineer")

st.sidebar.markdown("""
### How it works:
1. **Upload Resume**: PDF or Word (.docx) formats supported.
2. **Input Job Details**: Paste the job description you are targeting.
3. **ATS & Gap Checks**: Scans for format, metrics, keyword matching, and structure.
4. **Generate Tailored Resume**: AI rewrites details matching target JD and prepares Word/PDF files.
""")

# Initialize Session State for preserving results across rerenders
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "gap_results" not in st.session_state:
    st.session_state.gap_results = None
if "tailored_resume" not in st.session_state:
    st.session_state.tailored_resume = None
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "last_hash" not in st.session_state:
    st.session_state.last_hash = ""

# File uploader and job description input area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📁 Upload Resume or CV")
    uploaded_file = st.file_uploader("Drop your PDF or DOCX file here", type=["pdf", "docx"])
    
with col2:
    st.subheader("📋 Target Job Description")
    job_description = st.text_area("Paste the job listing/description here", height=150, placeholder="Paste details here...")

# Run Analysis Button
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 Analyze Resume & Scoring", type="primary", use_container_width=True):
    if not api_key:
        st.error(f"Please enter a valid {provider} API Key in the sidebar.")
    elif not uploaded_file:
        st.error("Please upload a resume file (PDF or DOCX).")
    elif not job_description.strip():
        st.error("Please paste the target job description.")
    else:
        with st.spinner("Analyzing resume content, parsing structures and generating scores..."):
            try:
                # 1. Extract Text
                # Copy file contents to bytes
                file_bytes = io.BytesIO(uploaded_file.read())
                resume_text = extract_text(file_bytes, uploaded_file.name)
                st.session_state.resume_text = resume_text

                # 2. Init Service based on active provider
                if provider == "Google Gemini":
                    service = GeminiResumeService(api_key=api_key)
                else:
                    service = GroqResumeService(api_key=api_key)
                
                # 3. Analyze Resume and scoring
                analysis = service.analyze_resume(resume_text, job_description, model_name=model_selection)
                st.session_state.analysis_results = analysis
                
                # 4. Analyze Gaps
                gaps = service.analyze_gaps(resume_text, job_description, model_name=model_selection)
                st.session_state.gap_results = gaps
                
                # Reset tailored resume since we have a new input
                st.session_state.tailored_resume = None
                
                st.success("Analysis complete!")
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")

# Display results if available
if st.session_state.analysis_results and st.session_state.gap_results:
    analysis = st.session_state.analysis_results
    gaps = st.session_state.gap_results
    
    # Create beautiful score layout
    st.markdown("---")
    st.header("📊 ATS Scorecard & Analysis")
    
    # Calculate score coloring classes
    def get_color_class(val):
        if val >= 80: return "score-green"
        elif val >= 55: return "score-yellow"
        else: return "score-red"
        
    overall_class = get_color_class(analysis.overall_score)
    kw_class = get_color_class(analysis.keyword_match_score)
    format_class = get_color_class(analysis.formatting_score)
    impact_class = get_color_class(analysis.experience_impact_score)
    
    st.markdown(f"""
    <div class="card-container">
        <div class="metric-card {overall_class}">
            <div class="metric-value">{analysis.overall_score}</div>
            <div class="metric-label">Overall Match</div>
        </div>
        <div class="metric-card {kw_class}">
            <div class="metric-value">{analysis.keyword_match_score}</div>
            <div class="metric-label">Keyword Fit</div>
        </div>
        <div class="metric-card {format_class}">
            <div class="metric-value">{analysis.formatting_score}</div>
            <div class="metric-label">Format Check</div>
        </div>
        <div class="metric-card {impact_class}">
            <div class="metric-value">{analysis.experience_impact_score}</div>
            <div class="metric-label">Impact & Metrics</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs for displaying detailed feedback
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Scoring & Summary", 
        "🔍 Keyword Gap Analysis", 
        "🛠️ Actionable Recommendations", 
        "✨ AI Tailored Resume Generator"
    ])
    
    with tab1:
        col_summary, col_checks = st.columns([2, 1])
        
        with col_summary:
            st.subheader("Recruiter Summary")
            st.markdown(f"<div class='info-box'>{analysis.summary_feedback}</div>", unsafe_allow_html=True)
            
            st.subheader("Key Strengths & Critical Notes")
            for rec in analysis.detailed_recommendations[:3]:
                st.markdown(f"✅ {rec}")
                
        with col_checks:
            st.subheader("Systems Check")
            
            checks = [
                ("Contact Details", analysis.contact_info_check),
                ("Standard Headings", analysis.headings_check),
                ("Length Limit", analysis.length_check),
                ("Action Verbs Usage", analysis.action_verbs_check)
            ]
            
            for label, status in checks:
                icon = "🟢 PASS" if status.score >= 70 else "🔴 FAIL"
                score_str = f"({status.score}/100)"
                st.markdown(f"**{label}**: {icon} {score_str}")
                st.caption(status.feedback)
                st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.15;'>", unsafe_allow_html=True)

    with tab2:
        st.subheader("Gap Analysis Summary")
        st.info(gaps.overall_gap_summary)
        
        col_kw, col_soft = st.columns([2, 1])
        
        with col_kw:
            st.subheader("Technical Keywords & Experience Gaps")
            if gaps.keywords:
                # Convert to dataframe for clean table display
                kw_data = []
                for kw in gaps.keywords:
                    kw_data.append({
                        "Keyword / Tool": kw.keyword,
                        "Match Status": "✅ Present" if kw.match_status.lower() == "present" else "❌ Missing",
                        "Importance": kw.importance,
                        "Action / Context": kw.context_or_recommendation
                    })
                df_kw = pd.DataFrame(kw_data)
                st.dataframe(df_kw, use_container_width=True, hide_index=True)
            else:
                st.write("No keyword details found.")
                
        with col_soft:
            st.subheader("Soft Skills Comparison")
            if gaps.soft_skills:
                for skill in gaps.soft_skills:
                    status_icon = "🟢" if skill.match_status.lower() == "present" else "🟡"
                    status_label = "Present" if skill.match_status.lower() == "present" else "Missing"
                    st.write(f"{status_icon} **{skill.skill}** - *{status_label}*")
            else:
                st.write("No soft skill details found.")

    with tab3:
        st.subheader("Detailed Suggestions to Improve Your Resume")
        st.write("Implement these suggestions in your current resume to directly boost your ATS ranking:")
        for idx, rec in enumerate(analysis.detailed_recommendations):
            st.markdown(f"**{idx + 1}.** {rec}")
            
    with tab4:
        st.subheader("✨ Generate Optimized Resume")
        st.write("Let AI restructure and rewrite your resume dynamically. It will optimize your wording, incorporate missing keywords, format details professionally, and prepare the content for instant download.")
        
        # Generator controls
        if provider == "Google Gemini":
            model_options = ["gemini-2.5-pro", "gemini-2.5-flash"]
            help_text = "Pro is highly recommended for rewriting resume text to be persuasive and professional."
        else:
            model_options = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
            help_text = "Llama-3.3-70b is highly recommended for rewriting resume text."
            
        model_generation = st.selectbox(
            "Rewrite Model Choice", 
            options=model_options,
            help=help_text
        )
        
        if st.button("Generate Tailored Resume Content", type="primary"):
            model_desc = "Gemini Pro" if provider == "Google Gemini" else "Llama 3.3"
            with st.spinner(f"Rewriting resume matching job requirements (this might take 20-30 seconds with {model_desc})..."):
                try:
                    if provider == "Google Gemini":
                        service = GeminiResumeService(api_key=api_key)
                    else:
                        service = GroqResumeService(api_key=api_key)
                        
                    tailored = service.generate_optimized_resume(
                        resume_text=st.session_state.resume_text,
                        job_description=job_description,
                        feedback_suggestions=analysis.detailed_recommendations,
                        model_name=model_generation
                    )
                    st.session_state.tailored_resume = tailored
                    st.success("Resume tailored successfully!")
                except Exception as e:
                    st.error(f"Tailoring failed: {str(e)}")
                    
        # Show download options if tailored resume exists
        if st.session_state.tailored_resume:
            tailored = st.session_state.tailored_resume
            
            st.markdown("---")
            st.subheader("⬇️ Download Exporters")
            
            theme_choice = st.selectbox(
                "Select PDF Theme Color",
                options=["Slate Modern", "Executive Navy", "Classic Charcoal", "Emerald Professional"]
            )
            
            # Action buttons side by side
            col_word, col_pdf = st.columns(2)
            
            with col_word:
                try:
                    docx_buffer = export_to_docx(tailored)
                    st.download_button(
                        label="📥 Download Word (.docx)",
                        data=docx_buffer,
                        file_name=f"Tailored_Resume_{tailored.contact_info.full_name.replace(' ', '_')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error creating Word file: {e}")
                    
            with col_pdf:
                try:
                    pdf_buffer = export_to_pdf(tailored, theme_name=theme_choice)
                    st.download_button(
                        label="📥 Download PDF (.pdf)",
                        data=pdf_buffer,
                        file_name=f"Tailored_Resume_{tailored.contact_info.full_name.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error creating PDF file: {e}")

            # Preview the tailored resume
            st.markdown("---")
            st.subheader("👀 Preview Optimized Content")
            
            # Format preview in clean Markdown
            preview_md = f"""
            # {tailored.contact_info.full_name}
            **Email**: {tailored.contact_info.email} | **Phone**: {tailored.contact_info.phone} | **Location**: {tailored.contact_info.location}
            """
            if tailored.contact_info.linkedin or tailored.contact_info.portfolio_or_website:
                preview_md += f"\n**Links**: {tailored.contact_info.linkedin} | {tailored.contact_info.portfolio_or_website}\n"
                
            preview_md += f"\n## Professional Summary\n{tailored.summary}\n"
            
            preview_md += "\n## Experience\n"
            for exp in tailored.experience:
                preview_md += f"\n### {exp.job_title} - {exp.company} ({exp.location})\n"
                preview_md += f"*{exp.start_date} to {exp.end_date}*\n"
                for bullet in exp.bullets:
                    preview_md += f"- {bullet}\n"
                    
            preview_md += "\n## Skills\n"
            preview_md += ", ".join(tailored.skills) + "\n"
            
            if tailored.projects:
                preview_md += "\n## Projects\n"
                for proj in tailored.projects:
                    preview_md += f"\n### {proj.title}\n"
                    preview_md += f"*Technologies: {', '.join(proj.technologies)}*\n"
                    if proj.link:
                        preview_md += f"*Link: {proj.link}*\n"
                    preview_md += f"{proj.description}\n"
                    
            preview_md += "\n## Education\n"
            for edu in tailored.education:
                preview_md += f"- **{edu.degree} in {edu.major}**, {edu.institution} ({edu.graduation_date})\n"
                
            if tailored.certifications:
                preview_md += "\n## Certifications\n"
                preview_md += ", ".join(tailored.certifications) + "\n"
                
            st.markdown(preview_md)
else:
    # Warm landing state when no analysis is loaded
    st.info("👋 Upload a Resume (PDF/DOCX) and paste a Target Job Description above, then click 'Analyze Resume & Scoring' to start.")
    
    # Feature Showcase Grid
    st.markdown("""
    <div style="margin-top: 40px;">
        <h3 style="text-align: center; margin-bottom: 25px;">Core Features & Integrations</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
            <div style="background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); padding: 20px; border-radius: 10px;">
                <h4 style="margin: 0 0 10px 0; color: #3b82f6;">⚡ Real-time Analysis</h4>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.85;">Connected directly to Gemini API for near-instant responses, scoring matches and formats within seconds.</p>
            </div>
            <div style="background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); padding: 20px; border-radius: 10px;">
                <h4 style="margin: 0 0 10px 0; color: #10b981;">📊 Multi-check scoring</h4>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.85;">Checks keyword frequencies, structural components (headings), and formatting issues standard ATS screeners look for.</p>
            </div>
            <div style="background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); padding: 20px; border-radius: 10px;">
                <h4 style="margin: 0 0 10px 0; color: #f59e0b;">✨ One-click Exporter</h4>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.85;">Instantly download the revised resume in clean Word format or in stunning, styled PDFs using custom visual layout engines.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
