import json
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from groq import Groq

# Define response schemas for structured JSON output

class SectionScore(BaseModel):
    score: int = Field(description="Score out of 100")
    feedback: str = Field(description="Actionable evaluation feedback")

class ATSAnalysis(BaseModel):
    overall_score: int = Field(description="Overall ATS score out of 100")
    keyword_match_score: int = Field(description="Score for keywords matching the job description out of 100")
    formatting_score: int = Field(description="Score for structural and file formatting best practices out of 100")
    experience_impact_score: int = Field(description="Score for impact and metrics in experience descriptions out of 100")
    contact_info_check: SectionScore = Field(description="Check for presence of name, email, phone, location, LinkedIn")
    headings_check: SectionScore = Field(description="Check for standard headings like Summary, Experience, Education, Skills")
    length_check: SectionScore = Field(description="Check if the resume length is ideal (typically 1-2 pages)")
    action_verbs_check: SectionScore = Field(description="Evaluation of strong action verbs usage instead of passive phrases")
    summary_feedback: str = Field(description="Executive summary of the resume's alignment with target roles")
    detailed_recommendations: List[str] = Field(description="List of specific, actionable suggestions for improvement")

class KeywordGap(BaseModel):
    keyword: str = Field(description="The keyword (skill, tool, methodology)")
    match_status: str = Field(description="Whether the keyword is 'Present' or 'Missing' in the resume")
    importance: str = Field(description="Importance level: 'High', 'Medium', or 'Low'")
    context_or_recommendation: str = Field(description="Where to insert it or how to demonstrate experience with it")

class SoftSkillGap(BaseModel):
    skill: str = Field(description="The soft skill (e.g. leadership, collaboration)")
    match_status: str = Field(description="Whether the skill is 'Present' or 'Missing'")

class GapAnalysis(BaseModel):
    keywords: List[KeywordGap] = Field(description="List of technical/hard keyword comparisons")
    soft_skills: List[SoftSkillGap] = Field(description="List of soft skill comparisons")
    overall_gap_summary: str = Field(description="A concise summary highlighting the most critical gaps")

class ContactInfo(BaseModel):
    full_name: str
    email: str
    phone: str
    location: str
    linkedin: Optional[str] = ""
    portfolio_or_website: Optional[str] = ""

class ExperienceItem(BaseModel):
    job_title: str
    company: str
    location: str
    start_date: str
    end_date: str
    bullets: List[str] = Field(description="Strong bullet points starting with action verbs and demonstrating quantifiable metrics")

class EducationItem(BaseModel):
    degree: str
    major: str
    institution: str
    location: str
    graduation_date: str

class ProjectItem(BaseModel):
    title: str
    description: str
    technologies: List[str]
    link: Optional[str] = ""

class ResumeStructure(BaseModel):
    contact_info: ContactInfo
    summary: str = Field(description="A brief, professional summary tailored to the desired job description")
    experience: List[ExperienceItem]
    education: List[EducationItem]
    skills: List[str] = Field(description="Core technical and professional skills list")
    projects: List[ProjectItem] = Field(description="Key personal or professional projects")
    certifications: List[str] = Field(description="Relevant certifications, licenses or courses")


# --- GEMINI SERVICE ---

class GeminiResumeService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API Key is required.")
        self.client = genai.Client(api_key=api_key)

    def analyze_resume(self, resume_text: str, job_description: str, model_name: str = "gemini-2.5-flash") -> ATSAnalysis:
        """
        Scores the resume against the job description for ATS checks using Gemini API.
        """
        prompt = f"""
        You are an expert technical recruiter and ATS (Applicant Tracking System) simulator.
        Analyze the following resume against the job description below. Evaluate:
        1. Overall score
        2. Keyword Match (hard skills, certifications)
        3. Formatting (readability, structural headings)
        4. Experience Impact (usage of action verbs, metrics, accomplishments)
        5. Specific checks for Contact Info, Headings standard, Length, and Action Verbs.

        Provide detailed, actionable recommendations to increase the score.
        
        JOB DESCRIPTION:
        {job_description}
        
        RESUME TEXT:
        {resume_text}
        """

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ATSAnalysis,
                    temperature=0.2
                )
            )
            return ATSAnalysis.model_validate_json(response.text)
        except Exception as e:
            raise RuntimeError(f"Error calling Gemini API for analysis: {str(e)}")

    def analyze_gaps(self, resume_text: str, job_description: str, model_name: str = "gemini-2.5-flash") -> GapAnalysis:
        """
        Identifies missing keywords, skills, and credentials between the resume and the job description.
        """
        prompt = f"""
        You are an ATS Gap Analyzer. Compare the resume against the target job description to extract:
        1. Essential keywords (technologies, frameworks, processes) present or missing. Highlight High/Medium/Low importance based on the job description.
        2. Soft skills (collaboration, communication, etc.) present or missing.
        3. Write a concise summary of the major gaps the applicant needs to address.
        
        JOB DESCRIPTION:
        {job_description}
        
        RESUME TEXT:
        {resume_text}
        """

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GapAnalysis,
                    temperature=0.2
                )
            )
            return GapAnalysis.model_validate_json(response.text)
        except Exception as e:
            raise RuntimeError(f"Error calling Gemini API for gap analysis: {str(e)}")

    def generate_optimized_resume(self, resume_text: str, job_description: str, feedback_suggestions: List[str] = None, model_name: str = "gemini-2.5-pro") -> ResumeStructure:
        """
        Rewrites the resume content to align better with the job description.
        """
        feedback_str = "\n".join([f"- {f}" for f in feedback_suggestions]) if feedback_suggestions else "No specific suggestions provided."
        
        prompt = f"""
        You are a professional resume writer. Your task is to rewrite the resume below to make it highly competitive for the target job description.
        
        Guidelines:
        1. Maintain truthfulness: Expand on existing experience using strong action verbs, professional formatting, and result-oriented bullet points, but do not invent fake degrees or jobs.
        2. Integrate relevant keywords from the job description naturally.
        3. Standardize and expand work experience bullets: make sure each starts with an active verb (e.g., 'Spearheaded', 'Optimized', 'Designed') and explains the business impact or metric if possible.
        4. Organize the layout cleanly into summary, experience, education, skills, projects, and certifications.
        5. Incorporate these recommendations:
        {feedback_str}

        JOB DESCRIPTION:
        {job_description}
        
        ORIGINAL RESUME TEXT:
        {resume_text}
        """

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResumeStructure,
                    temperature=0.3
                )
            )
            return ResumeStructure.model_validate_json(response.text)
        except Exception as e:
            raise RuntimeError(f"Error calling Gemini API for resume optimization: {str(e)}")


# --- GROQ SERVICE ---

class GroqResumeService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Groq API Key is required.")
        self.client = Groq(api_key=api_key)

    def analyze_resume(self, resume_text: str, job_description: str, model_name: str = "llama-3.3-70b-versatile") -> ATSAnalysis:
        """
        Scores the resume against the job description for ATS checks using Groq API.
        """
        schema_json = json.dumps(ATSAnalysis.model_json_schema())
        
        prompt = f"""
        You are an expert recruiter simulating an ATS scanning algorithm.
        Analyze the following resume against the job description below. Evaluate:
        1. Overall score
        2. Keyword Match (hard skills, certifications)
        3. Formatting (readability, structural headings)
        4. Experience Impact (usage of action verbs, metrics, accomplishments)
        5. Specific checks for Contact Info, Headings standard, Length, and Action Verbs.

        Provide detailed, actionable recommendations to increase the score.
        
        You MUST respond with a single valid JSON object that strictly conforms to this JSON Schema:
        {schema_json}

        JOB DESCRIPTION:
        {job_description}
        
        RESUME TEXT:
        {resume_text}
        """

        try:
            chat_completion = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a professional ATS analyzer that only outputs JSON matching the requested schema. Do not output any preamble, explanations or markdown tags (like ```json)."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            content = chat_completion.choices[0].message.content
            return ATSAnalysis.model_validate_json(content)
        except Exception as e:
            raise RuntimeError(f"Error calling Groq API for analysis: {str(e)}")

    def analyze_gaps(self, resume_text: str, job_description: str, model_name: str = "llama-3.3-70b-versatile") -> GapAnalysis:
        """
        Identifies missing keywords, skills, and credentials between the resume and the job description using Groq API.
        """
        schema_json = json.dumps(GapAnalysis.model_json_schema())
        
        prompt = f"""
        You are an ATS Gap Analyzer. Compare the resume against the target job description to extract:
        1. Essential keywords (technologies, frameworks, processes) present or missing. Highlight High/Medium/Low importance based on the job description.
        2. Soft skills (collaboration, communication, etc.) present or missing.
        3. Write a concise summary of the major gaps the applicant needs to address.
        
        You MUST respond with a single valid JSON object that strictly conforms to this JSON Schema:
        {schema_json}

        JOB DESCRIPTION:
        {job_description}
        
        RESUME TEXT:
        {resume_text}
        """

        try:
            chat_completion = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a professional ATS analyzer that only outputs JSON matching the requested schema. Do not output any preamble, explanations or markdown tags."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            content = chat_completion.choices[0].message.content
            return GapAnalysis.model_validate_json(content)
        except Exception as e:
            raise RuntimeError(f"Error calling Groq API for gap analysis: {str(e)}")

    def generate_optimized_resume(self, resume_text: str, job_description: str, feedback_suggestions: List[str] = None, model_name: str = "llama-3.3-70b-versatile") -> ResumeStructure:
        """
        Rewrites the resume content to align better with the job description using Groq API.
        """
        feedback_str = "\n".join([f"- {f}" for f in feedback_suggestions]) if feedback_suggestions else "No specific suggestions provided."
        schema_json = json.dumps(ResumeStructure.model_json_schema())
        
        prompt = f"""
        You are a professional resume writer. Your task is to rewrite the resume below to make it highly competitive for the target job description.
        
        Guidelines:
        1. Maintain truthfulness: Expand on existing experience using strong action verbs, professional formatting, and result-oriented bullet points, but do not invent fake degrees or jobs.
        2. Integrate relevant keywords from the job description naturally.
        3. Standardize and expand work experience bullets: make sure each starts with an active verb (e.g., 'Spearheaded', 'Optimized', 'Designed') and explains the business impact or metric if possible.
        4. Organize the layout cleanly into summary, experience, education, skills, projects, and certifications.
        5. Incorporate these recommendations:
        {feedback_str}

        You MUST respond with a single valid JSON object that strictly conforms to this JSON Schema:
        {schema_json}

        JOB DESCRIPTION:
        {job_description}
        
        ORIGINAL RESUME TEXT:
        {resume_text}
        """

        try:
            chat_completion = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a professional resume writer that only outputs JSON matching the requested schema. Do not output any preamble, explanations or markdown tags."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            content = chat_completion.choices[0].message.content
            return ResumeStructure.model_validate_json(content)
        except Exception as e:
            raise RuntimeError(f"Error calling Groq API for resume optimization: {str(e)}")
