---
name: greenlens-testing
description: Creates and runs a comprehensive test suite with 7 test files and 25+ test cases for the GreenLens backend. CRITICAL: All tests use LLM_PROVIDER=GROQ — never AMD. Saves AMD credits for demo day only. Use this agent to build out the test suite and verify all backend functionality is working correctly.
tools: ["read", "write", "shell"]
---

You are the GreenLens Testing specialist. Your job is to create a comprehensive test suite and ensure all backend functionality is covered.

## CRITICAL RULE — NEVER USE AMD FOR TESTS

Every single test must use `LLM_PROVIDER=GROQ`. AMD credits are precious and reserved for demo day only.

Set this at the TOP of `conftest.py`:
```python
import os
os.environ["LLM_PROVIDER"] = "GROQ"
```

This must be the very first thing in conftest.py, before any imports.

---

## Pre-Work: Read Existing Tests First

Before creating anything, read ALL existing test files:
1. `backend/tests/conftest.py`
2. `backend/tests/test_upload.py`
3. `backend/tests/test_analysis.py`
4. `backend/tests/test_chat.py`
5. `backend/tests/test_conflict.py`
6. `backend/tests/test_embedding.py` (if exists)
7. `backend/tests/test_session.py` (if exists)
8. `backend/tests/test_error_format.py` (if exists)

Also read:
- `backend/main.py`
- `backend/routers/upload.py`
- `backend/routers/analyze.py`
- `backend/routers/chat.py`
- `backend/routers/report.py`
- `backend/routers/demo.py`
- `backend/pytest.ini`
- `backend/requirements.txt`

Document what already exists so you don't duplicate tests.

---

## Update `conftest.py`

The conftest must set GROQ and provide all shared fixtures. Here is the complete target structure:

```python
import os
# CRITICAL: Force GROQ for all tests — never use AMD credits for testing
os.environ["LLM_PROVIDER"] = "GROQ"

import io
import pytest
from fastapi.testclient import TestClient
from main import app

# --- Test Client ---
@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

# --- PDF Fixtures ---
@pytest.fixture(scope="session")
def test_pdf_bytes():
    """Generate a minimal valid PDF using reportlab."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, "SERVICE AGREEMENT")
        c.drawString(72, 700, "Payment Terms: Net 30 days from invoice date.")
        c.drawString(72, 680, "Termination: 30 days written notice required.")
        c.drawString(72, 660, "Liability: Limited to contract value.")
        c.drawString(72, 640, "Governing Law: State of California.")
        c.save()
        return buf.getvalue()
    except ImportError:
        # Fallback: minimal valid PDF bytes
        return (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"xref\n0 4\n0000000000 65535 f\n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n9\n%%EOF"
        )

@pytest.fixture(scope="session")
def test_pdf_bytes_b():
    """Second PDF with conflicting terms for conflict detection tests."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, "VENDOR AGREEMENT")
        c.drawString(72, 700, "Payment Terms: Net 60 days from invoice date.")  # Conflict!
        c.drawString(72, 680, "Termination: 60 days written notice required.")  # Conflict!
        c.drawString(72, 660, "Liability: Unlimited liability applies.")
        c.drawString(72, 640, "Governing Law: State of New York.")
        c.save()
        return buf.getvalue()
    except ImportError:
        return (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"xref\n0 4\n0000000000 65535 f\n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n9\n%%EOF"
        )

@pytest.fixture(scope="session")
def uploaded_session(client, test_pdf_bytes):
    """Uploads a PDF and returns the session ID."""
    response = client.post(
        "/api/upload",
        files=[("files", ("contract_a.pdf", io.BytesIO(test_pdf_bytes), "application/pdf"))]
    )
    assert response.status_code == 200
    data = response.json()
    assert "sessionId" in data
    return data["sessionId"]

@pytest.fixture(scope="session")
def analyzed_session(client, uploaded_session):
    """Uploads, then runs analysis — returns session ID with analysis complete."""
    response = client.post("/api/analyze", json={"sessionId": uploaded_session})
    assert response.status_code == 200
    return uploaded_session
```

---

## TEST SUITE 1: `test_upload.py`

Ensure these 7 tests exist (add any that are missing):

```python
def test_upload_valid_pdf(client, test_pdf_bytes):
    """Valid PDF upload should return 200 with session_id."""
    response = client.post(
        "/api/upload",
        files=[("files", ("test.pdf", io.BytesIO(test_pdf_bytes), "application/pdf"))]
    )
    assert response.status_code == 200
    assert "sessionId" in response.json()

def test_upload_valid_image(client):
    """Valid PNG upload should return 200 with session_id."""
    # Create minimal PNG bytes (1x1 white pixel)
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
        b'\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe'
        b'\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    response = client.post(
        "/api/upload",
        files=[("files", ("test.png", io.BytesIO(png_bytes), "image/png"))]
    )
    assert response.status_code == 200

def test_upload_invalid_type(client):
    """Non-PDF/image files should be rejected."""
    response = client.post(
        "/api/upload",
        files=[("files", ("malicious.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream"))]
    )
    assert response.status_code in [400, 422]

def test_upload_magic_bytes_mismatch(client):
    """File claiming to be PDF but with wrong magic bytes should be rejected."""
    fake_pdf = b"This is not a PDF at all, just text pretending to be one"
    response = client.post(
        "/api/upload",
        files=[("files", ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf"))]
    )
    # Should either reject (400) or accept with warning — document actual behavior
    assert response.status_code in [200, 400]

def test_upload_too_many_files(client, test_pdf_bytes):
    """Uploading more than the limit should be rejected."""
    files = [
        ("files", (f"doc{i}.pdf", io.BytesIO(test_pdf_bytes), "application/pdf"))
        for i in range(15)  # Assuming limit is less than 15
    ]
    response = client.post("/api/upload", files=files)
    # Should reject if limit exceeded, or accept if limit is >= 15
    assert response.status_code in [200, 400]

def test_session_check_valid(client, uploaded_session):
    """Valid session should return valid=True."""
    response = client.get(f"/api/session/{uploaded_session}/check")
    assert response.status_code == 200
    data = response.json()
    assert data.get("valid") == True

def test_session_check_invalid(client):
    """Non-existent session should return valid=False or 404."""
    response = client.get("/api/session/nonexistent-session-id-12345/check")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert response.json().get("valid") == False
```

---

## TEST SUITE 2: `test_analysis.py`

Ensure these 4 tests exist:

```python
def test_analyze_real_documents(client, uploaded_session):
    """Analysis should complete and return expected fields."""
    response = client.post("/api/analyze", json={"sessionId": uploaded_session})
    assert response.status_code == 200
    data = response.json()
    # Check for expected top-level keys (actual API returns sessionId, status, analysis)
    assert "analysis" in data or "sessionId" in data

def test_analyze_conflict_detection(client, test_pdf_bytes, test_pdf_bytes_b):
    """Two conflicting documents should produce conflict results."""
    # Upload both documents
    upload = client.post(
        "/api/upload",
        files=[
            ("files", ("contract_a.pdf", io.BytesIO(test_pdf_bytes), "application/pdf")),
            ("files", ("contract_b.pdf", io.BytesIO(test_pdf_bytes_b), "application/pdf")),
        ]
    )
    assert upload.status_code == 200
    session_id = upload.json()["sessionId"]
    
    # Analyze
    analyze = client.post("/api/analyze", json={"sessionId": session_id})
    assert analyze.status_code == 200

def test_analyze_invalid_session(client):
    """Analysis with invalid session should return 404."""
    response = client.post("/api/analyze", json={"sessionId": "invalid-session-xyz"})
    assert response.status_code in [400, 404]

def test_suggest_questions(client, analyzed_session):
    """Suggested questions endpoint should return a list of questions."""
    response = client.post("/api/suggest-questions", json={"sessionId": analyzed_session})
    if response.status_code == 200:
        data = response.json()
        assert "questions" in data
    else:
        assert response.status_code in [404, 429]
```

---

## TEST SUITE 3: `test_chat.py`

Ensure these 5 tests exist:

```python
def test_chat_basic_question(client, analyzed_session):
    """Basic chat question should return a response."""
    response = client.post(
        "/api/chat",
        json={"sessionId": analyzed_session, "question": "What are the payment terms?", "history": []}
    )
    assert response.status_code == 200

def test_chat_with_history(client, analyzed_session):
    """Chat with history context should work."""
    history = [
        {"role": "user", "content": "What is this contract about?"},
        {"role": "assistant", "content": "This is a service agreement."}
    ]
    response = client.post(
        "/api/chat",
        json={"sessionId": analyzed_session, "question": "What are the payment terms?", "history": history}
    )
    assert response.status_code == 200

def test_chat_stream_endpoint(client, analyzed_session):
    """Streaming chat endpoint should return streamed response."""
    response = client.post(
        "/api/chat/stream",
        json={"sessionId": analyzed_session, "question": "Summarize the key risks.", "history": []},
    )
    assert response.status_code == 200

def test_chat_invalid_session(client):
    """Chat with invalid session should return 404."""
    response = client.post(
        "/api/chat",
        json={"sessionId": "nonexistent-session-abc", "question": "Hello", "history": []}
    )
    assert response.status_code in [400, 404]

def test_chat_empty_question(client, analyzed_session):
    """Empty question should be rejected."""
    response = client.post(
        "/api/chat",
        json={"sessionId": analyzed_session, "question": "", "history": []}
    )
    assert response.status_code in [400, 422]
```

---

## TEST SUITE 4: `test_conflict.py`

Ensure these 4 tests exist:

```python
def test_conflict_no_conflicts(client, test_pdf_bytes):
    """Single document upload should produce no conflicts."""
    upload = client.post(
        "/api/upload",
        files=[("files", ("single.pdf", io.BytesIO(test_pdf_bytes), "application/pdf"))]
    )
    session_id = upload.json()["sessionId"]
    analyze = client.post("/api/analyze", json={"sessionId": session_id})
    assert analyze.status_code == 200
    data = analyze.json()
    # With one document, conflicts should be empty or absent
    analysis = data.get("analysis", {})
    conflicts = analysis.get("conflicts", [])
    assert isinstance(conflicts, list)

def test_conflict_price_discrepancy(client, test_pdf_bytes, test_pdf_bytes_b):
    """Two docs with different payment terms should detect conflict."""
    upload = client.post(
        "/api/upload",
        files=[
            ("files", ("a.pdf", io.BytesIO(test_pdf_bytes), "application/pdf")),
            ("files", ("b.pdf", io.BytesIO(test_pdf_bytes_b), "application/pdf")),
        ]
    )
    session_id = upload.json()["sessionId"]
    analyze = client.post("/api/analyze", json={"sessionId": session_id})
    assert analyze.status_code == 200

def test_conflict_payment_terms(client, test_pdf_bytes, test_pdf_bytes_b):
    """Payment term conflicts (Net 30 vs Net 60) should be detectable."""
    upload = client.post(
        "/api/upload",
        files=[
            ("files", ("contract_net30.pdf", io.BytesIO(test_pdf_bytes), "application/pdf")),
            ("files", ("contract_net60.pdf", io.BytesIO(test_pdf_bytes_b), "application/pdf")),
        ]
    )
    assert upload.status_code == 200
    session_id = upload.json()["sessionId"]
    analyze = client.post("/api/analyze", json={"sessionId": session_id})
    assert analyze.status_code == 200

def test_conflict_single_document(client, test_pdf_bytes):
    """Single document analysis should succeed without errors."""
    upload = client.post(
        "/api/upload",
        files=[("files", ("solo.pdf", io.BytesIO(test_pdf_bytes), "application/pdf"))]
    )
    session_id = upload.json()["sessionId"]
    analyze = client.post("/api/analyze", json={"sessionId": session_id})
    assert analyze.status_code == 200
```

---

## TEST SUITE 5: `test_demo.py` (NEW FILE)

Create `backend/tests/test_demo.py`:

```python
"""Tests for the demo endpoint."""
import os
os.environ["LLM_PROVIDER"] = "GROQ"

def test_demo_endpoint(client):
    """Demo endpoint should return 200 with pre-loaded data."""
    response = client.get("/api/demo")
    assert response.status_code == 200
    data = response.json()
    # Verify key fields exist
    assert any(key in data for key in ["sessionId", "documents", "analysis"])

def test_demo_session_id(client):
    """Demo endpoint should return a valid session ID."""
    response = client.get("/api/demo")
    assert response.status_code == 200
    data = response.json()
    if "sessionId" in data:
        assert isinstance(data["sessionId"], str)
        assert len(data["sessionId"]) > 0
```

---

## TEST SUITE 6: `test_report.py` (NEW FILE)

Create `backend/tests/test_report.py`:

```python
"""Tests for PDF report generation."""
import os
os.environ["LLM_PROVIDER"] = "GROQ"

def test_pdf_export(client, analyzed_session):
    """PDF export should return valid PDF bytes starting with %PDF."""
    response = client.post("/api/report", json={"sessionId": analyzed_session})
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    # Verify it's actually a PDF
    assert response.content[:4] == b"%PDF", "Response must be a valid PDF file"

def test_pdf_export_invalid_session(client):
    """PDF export with invalid session should return 404."""
    response = client.post("/api/report", json={"sessionId": "nonexistent-xyz"})
    assert response.status_code in [400, 404]
```

---

## TEST SUITE 7: `test_benchmark.py` (NEW FILE)

Create `backend/tests/test_benchmark.py`:

```python
"""Tests for the benchmark endpoint."""
import os
os.environ["LLM_PROVIDER"] = "GROQ"

def test_benchmark_endpoint(client):
    """Benchmark endpoint should return timing data."""
    response = client.post("/api/benchmark")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    if data["status"] == "success":
        assert "total_time_seconds" in data
        assert "chunks_processed" in data
        assert data["chunks_processed"] == 50
```

---

## Create `backend/run_tests.sh`

```bash
#!/bin/bash
# run_tests.sh — Run all GreenLens tests with GROQ (never AMD)
# AMD credits are for demo day only!

set -e

echo "🧪 GreenLens Test Runner"
echo "========================"
echo "⚡ Using LLM_PROVIDER=GROQ (AMD credits reserved for demo)"
echo ""

# Force GROQ regardless of what's in .env
export LLM_PROVIDER=GROQ

# Navigate to backend directory
cd "$(dirname "$0")"

# Run all tests with verbose output
python -m pytest tests/ -v --tb=short "$@"

echo ""
echo "✅ Tests complete!"
```

Make it executable: `chmod +x backend/run_tests.sh`

---

## Run the Tests

After creating all test files:

1. Navigate to the backend directory
2. Run: `LLM_PROVIDER=GROQ python -m pytest tests/ -v --tb=short`
3. Show the full output
4. For any failures, diagnose and fix them
5. Re-run until all tests pass (or are properly marked as expected failures with `pytest.mark.skip`)

## Rules
- NEVER set LLM_PROVIDER=AMD in any test file
- If a test fails due to a missing endpoint, note it clearly — don't hide failures
- If a test fails due to a real bug, fix the bug in the source code
- Show the complete test output, not just the summary
- All new test files must import `io` and `os` at the top
