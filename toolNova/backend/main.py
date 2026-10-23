from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
import subprocess
from pathlib import Path

# --- CONFIGURATION TESSERACT ---
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = FastAPI(title="ToolNova API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("temp/uploads")
RESULT_DIR = Path("temp/results")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/health")
async def health_check():
    return {"status": "online", "message": "ToolNova Backend is running"}

# --- PDF SERVICES ---
@app.post("/api/pdf/merge")
async def merge_pdfs(files: list[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least two PDF files are required")
    job_id = str(uuid.uuid4())
    output_filename = f"merged_{job_id}.pdf"
    output_path = RESULT_DIR / output_filename
    try:
        import fitz
        merged_pdf = fitz.open()
        for file in files:
            temp_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            merged_pdf.insert_pdf(fitz.open(temp_path))
        merged_pdf.save(output_path)
        merged_pdf.close()
        return {"download_url": f"/download/{output_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pdf/split")
async def split_pdf(file: UploadFile = File(...), start_page: int = Form(...), end_page: int = Form(...)):
    job_id = str(uuid.uuid4())
    output_filename = f"split_{job_id}.pdf"
    output_path = RESULT_DIR / output_filename
    try:
        import fitz
        temp_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        doc = fitz.open(temp_path)
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start_page-1, to_page=end_page-1)
        new_doc.save(output_path)
        new_doc.close()
        doc.close()
        return {"download_url": f"/download/{output_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- OCR SERVICE ---
@app.post("/api/text/ocr")
async def ocr_image(file: UploadFile = File(...)):
    try:
        from PIL import Image
        import io
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(image)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- AI SERVICES ---
@app.post("/api/images/remove-bg")
async def remove_background(file: UploadFile = File(...)):
    try:
        from rembg import remove
        from PIL import Image
        import io
        input_data = await file.read()
        input_image = Image.open(io.BytesIO(input_data))
        output_image = remove(input_image)
        job_id = str(uuid.uuid4())
        output_filename = f"nobg_{job_id}.png"
        output_path = RESULT_DIR / output_filename
        output_image.save(output_path)
        return {"download_url": f"/download/{output_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/text/rewrite")
async def rewrite_text(text: str = Form(...), style: str = Form(...)):
    styles = {"professional": "Professional Version: ", "simple": "Simple Version: ", "concise": "Concise Version: "}
    prefix = styles.get(style, "")
    rewritten = f"{prefix} {text}"
    return {"rewritten_text": rewritten}

# --- MEDIA SERVICES (FFMPEG) ---

@app.post("/api/media/compress-video")
async def compress_video(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    output_filename = f"compressed_{job_id}.mp4"
    output_path = RESULT_DIR / output_filename

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Basic compression using CRF 28 (reasonable quality/size trade-off)
        cmd = f'ffmpeg -i "{input_path}" -vcodec libx264 -crf 28 "{output_path}"'
        subprocess.run(cmd, shell=True, check=True)
        return {"download_url": f"/download/{output_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/media/extract-audio")
async def extract_audio(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    output_filename = f"audio_{job_id}.mp3"
    output_path = RESULT_DIR / output_filename

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        cmd = f'ffmpeg -i "{input_path}" -vn -acodec libmp3lame -q:a 2 "{output_path}"'
        subprocess.run(cmd, shell=True, check=True)
        return {"download_url": f"/download/{output_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/media/convert-audio")
async def convert_audio(file: UploadFile = File(...), target_format: str = Form(...)):
    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    output_filename = f"converted_{job_id}.{target_format}"
    output_path = RESULT_DIR / output_filename

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        cmd = f'ffmpeg -i "{input_path}" "{output_path}"'
        subprocess.run(cmd, shell=True, check=True)
        return {"download_url": f"/download/{output_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- DOWNLOAD ENDPOINT ---
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = RESULT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
