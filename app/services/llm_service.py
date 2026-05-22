import os
import json
from google import genai

# Initialize client using new google-genai SDK
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


async def generate_test_cases_from_text(content: str, context: str = None) -> list:
    """
    Takes raw text extracted from the uploaded requirements document
    and an optional context string to tune test case generation.

    - Without context: generates generic but comprehensive test cases.
    - With context: uses real values, roles, URLs, and specifics from the context
      instead of placeholders like 'valid email' or 'example.com'.
    """

    context_section = ""
    if context:
        context_section = f"""
You have also been provided a context file with specific details about this application.
Use this context to make your test cases as specific and realistic as possible.
Replace any generic placeholders (like "valid email", "correct password", "example URL") 
with the real values, real user roles, real URLs, and real data found in the context below.

Context:
\"\"\"
{context}
\"\"\"
"""

    prompt = f"""
You are a senior QA engineer. Read the following requirements document
which contains user stories and acceptance criteria.
{context_section}
Generate comprehensive test cases covering:
- Positive test cases (happy path)
- Negative test cases (invalid inputs, wrong credentials, etc.)
- Edge cases (empty fields, boundary values, etc.)

Requirements document:
\"\"\"
{content}
\"\"\"

Return ONLY a valid JSON array. No explanation, no markdown, no code fences.
Each object in the array must have exactly these fields:
- "title": short name of the test case (string)
- "steps": list of step-by-step actions (array of strings)
- "expected_result": what should happen (string)
- "type": one of "positive", "negative", or "edge_case" (string)

Example of ONE item:
{{
  "title": "Login with valid credentials",
  "steps": ["Navigate to /login", "Enter valid email", "Enter correct password", "Click Login button"],
  "expected_result": "User is redirected to the dashboard",
  "type": "positive"
}}
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )
    raw = response.text.strip()

    # Strip markdown code fences if Gemini adds them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)