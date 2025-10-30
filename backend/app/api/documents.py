"""Document management API endpoints"""

import io
from pathlib import Path

from flask import jsonify, request

from app.api import api_bp
from core.document_store import DocumentStore
from core.errors import handle_errors

try:
    from PIL import Image
except ImportError:  # pragma: no cover - pillow should be installed in runtime env
    Image = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - pytesseract optional depending on build
    pytesseract = None


document_store = DocumentStore()


@api_bp.route("/documents/list", methods=["GET"])
@handle_errors
def list_documents():
    """List all uploaded documents"""
    try:
        documents = document_store.get_recent_documents(limit=50)
        return jsonify({"success": True, "documents": documents, "total": len(documents)})

    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Failed to list documents: {str(e)}"}),
            500,
        )


@api_bp.route("/documents/upload", methods=["POST"])
@handle_errors
def upload_document():
    """Upload a document"""
    try:
        if not Image or not pytesseract:
            return (
                jsonify({"success": False, "error": "OCR dependencies are not available"}),
                503,
            )

        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file part in request"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No selected file"}), 400

        # Read file and perform OCR
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))
        ocr_text = pytesseract.image_to_string(image)

        if not ocr_text.strip():
            return jsonify({"success": False, "error": "No text detected in uploaded document"}), 400

        file_extension = Path(file.filename).suffix.lstrip(".").lower() or "image"
        metadata = {
            "source": "upload",
            "ingestion_method": "ocr",
            "original_filename": file.filename,
            "file_extension": file_extension,
            "file_size": len(image_bytes),
        }

        doc_id = document_store.add_document(
            content=ocr_text,
            title=file.filename,
            file_path=None,
            doc_type=file_extension,
            metadata=metadata,
            user_id=None,
        )

        chunk_summary = document_store.chunk_manager.get_document_summary(doc_id)

        return jsonify({
            "success": True,
            "message": "Document uploaded and OCR processed",
            "document_id": doc_id,
            "ocr_text": ocr_text,
            "chunk_summary": chunk_summary,
        })

    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Failed to upload document: {str(e)}"}),
            500,
        )


@api_bp.route("/documents/<document_id>", methods=["DELETE"])
@handle_errors
def delete_document(document_id):
    """Delete a document"""
    try:
        # For now, return success - this would integrate with file service
        return jsonify(
            {
                "success": True,
                "message": f"Document {document_id} delete endpoint ready",
            }
        )

    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Failed to delete document: {str(e)}"}),
            500,
        )
