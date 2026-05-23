import json
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
from app.schemas.generate import GenerateTestResponse
from app.services.file_service import extract_text_from_file
from app.services.llm_service import (
    generate_test_cases_from_text,
    generate_test_cases_from_image,
    generate_test_cases_from_both
)
from app.database import db

router = APIRouter(prefix="/tests", tags=["generate"])

SUPPORTED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp"
}

SUPPORTED_DOC_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


def _is_image(file: UploadFile) -> bool:
    """Check if uploaded file is an image by content type or extension."""
    if file.content_type in SUPPORTED_IMAGE_TYPES:
        return True
    filename = file.filename.lower()
    return any(filename.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"])


@router.post("/generate", response_model=GenerateTestResponse)
async def generate_tests_from_document(
    file: Optional[UploadFile] = File(None, description="Requirements document (.txt, .pdf, .docx, .md) with user stories and acceptance criteria"),
    wireframe: Optional[UploadFile] = File(None, description="Wireframe or UI screenshot (.png, .jpg, .webp) — Gemini visually analyzes the UI and generates test cases from it"),
    context_file: Optional[UploadFile] = File(None, description="(Optional) Context file (.txt, .pdf, .md, .docx) with app-specific details like real URLs, user roles, and test data")
):
    """
    Generate test cases using Gemini. At least one of `file` or `wireframe` is required.

    **Options:**
    - Upload only a **requirements doc** → generates test cases from written user stories
    - Upload only a **wireframe/screenshot** → Gemini analyzes the UI and generates test cases from what it sees
    - Upload **both** → Gemini combines requirements + visual UI for the most complete test cases

    **Context file (always optional):** Provide app-specific details to replace generic
    placeholders with real values (actual URLs, credentials, user roles, etc.)
    """

    # Validate — at least one of file or wireframe must be provided
    has_doc = file and file.filename
    has_wireframe = wireframe and wireframe.filename

    if not has_doc and not has_wireframe:
        raise HTTPException(
            status_code=400,
            detail="At least one input is required: upload a requirements document, a wireframe/screenshot, or both."
        )

    # Extract requirements document text if provided
    content = None
    if has_doc:
        content = await extract_text_from_file(file)
        if len(content.strip()) < 20:
            raise HTTPException(
                status_code=400,
                detail="Requirements document appears to be empty or has too little content."
            )

    # Read wireframe image bytes if provided
    image_bytes = None
    media_type = None
    if has_wireframe:
        if not _is_image(wireframe):
            raise HTTPException(
                status_code=400,
                detail=f"Wireframe must be an image file (.png, .jpg, .jpeg, .webp). Got: {wireframe.filename}"
            )
        image_bytes = await wireframe.read()
        media_type = wireframe.content_type or "image/png"

    # Extract context if provided (discard after use)
    context = None
    if context_file and context_file.filename:
        try:
            context = await extract_text_from_file(context_file)
            if len(context.strip()) < 10:
                context = None
        except HTTPException:
            context = None  # Don't block generation if context fails

    # Call the appropriate Gemini function based on what was uploaded
    try:
        if has_doc and has_wireframe:
            # Both provided — combine for best results
            test_cases = await generate_test_cases_from_both(
                content=content,
                image_bytes=image_bytes,
                media_type=media_type,
                context=context
            )
            source = "document + wireframe"
        elif has_wireframe:
            # Wireframe only
            test_cases = await generate_test_cases_from_image(
                image_bytes=image_bytes,
                media_type=media_type,
                context=context
            )
            source = "wireframe"
        else:
            # Document only
            test_cases = await generate_test_cases_from_text(
                content=content,
                context=context
            )
            source = "document"

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

    # Use wireframe filename if no doc was uploaded
    filename = file.filename if has_doc else wireframe.filename

    # Save TestRun to DB
    run = await db.testrun.create(data={
        "filename": filename,
        "total": len(test_cases),
        "status": "completed"
    })

    # Save each test case linked to this run
    for tc in test_cases:
        await db.testresult.create(data={
            "runId": run.id,
            "title": tc.get("title", ""),
            "steps": json.dumps(tc.get("steps", [])),
            "expectedResult": tc.get("expected_result", ""),
            "type": tc.get("type", "")
        })

    return GenerateTestResponse(
        run_id=run.id,
        filename=filename,
        total=len(test_cases),
        context_used=context is not None,
        source=source,
        test_cases=test_cases
    )
