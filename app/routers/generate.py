import json
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
from app.schemas.generate import GenerateTestResponse
from app.services.file_service import extract_text_from_file
from app.services.llm_service import generate_test_cases_from_text
from app.database import db

router = APIRouter(prefix="/tests", tags=["generate"])


@router.post("/generate", response_model=GenerateTestResponse)
async def generate_tests_from_document(
    file: UploadFile = File(..., description="Upload a .txt, .pdf, or .docx requirements document with user stories and acceptance criteria"),
    context_file: Optional[UploadFile] = File(None, description="(Optional) Upload a context file (.txt, .pdf, .md, .docx) with app-specific details like real URLs, user roles, test data, and environment info to generate more specific test cases")
):
    """
    Upload a requirements document to generate test cases using Gemini.

    Optionally upload a context file to tune the output — instead of generic
    placeholders like 'valid email', Gemini will use real values from your context
    (actual URLs, credentials, user roles, environment details, etc.).

    Supported formats for both files: .txt, .md, .pdf, .docx
    """

    # Step 1: Extract text from the requirements file
    content = await extract_text_from_file(file)
    if len(content.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Requirements document appears to be empty or has too little content."
        )

    # Step 2: Extract text from context file if provided (discard after use)
    context = None
    if context_file and context_file.filename:
        try:
            context = await extract_text_from_file(context_file)
            if len(context.strip()) < 10:
                context = None  # Ignore if effectively empty
        except HTTPException:
            # If context file fails to parse, continue without it rather than blocking generation
            context = None

    # Step 3: Send to Gemini with optional context
    try:
        test_cases = await generate_test_cases_from_text(content, context=context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

    # Step 4: Save TestRun to database
    run = await db.testrun.create(data={
        "filename": file.filename,
        "total": len(test_cases),
        "status": "completed"
    })

    # Step 5: Save each test case as a TestResult linked to this run
    for tc in test_cases:
        await db.testresult.create(data={
            "runId": run.id,
            "title": tc.get("title", ""),
            "steps": json.dumps(tc.get("steps", [])),
            "expectedResult": tc.get("expected_result", ""),
            "type": tc.get("type", "")
        })

    return GenerateTestResponse(
        context_used=context is not None,
        run_id=run.id,
        filename=file.filename,
        total=len(test_cases),
        test_cases=test_cases
    )