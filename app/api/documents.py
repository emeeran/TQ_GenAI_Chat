"""Document management API endpoints"""

from flask import jsonify

from app.api import api_bp
from core.errors import handle_errors


@api_bp.route("/documents/list", methods=["GET"])
@handle_errors
def list_documents():
    """List all uploaded documents"""
    try:
        # For now, return empty list - this would integrate with file service
        return jsonify({"success": True, "documents": [], "total": 0})

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
        from flask import request
        import pytesseract
        from PIL import Image
        import io
        from core.context import ContextManager

        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file part in request"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No selected file"}), 400

        # Read file and perform OCR
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))
        ocr_text = pytesseract.image_to_string(image)

        # Store OCR text in context
        context_manager = ContextManager()
        doc_id = context_manager.add_document(file.filename, ocr_text, metadata={"source": "upload"})

        return jsonify({
            "success": True,
            "message": "Document uploaded and OCR processed",
            "document_id": doc_id,
            "ocr_text": ocr_text,
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
