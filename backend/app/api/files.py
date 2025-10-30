"""File API endpoints."""

from flask import jsonify

from app.api import api_bp


@api_bp.route("/files", methods=["GET"])
def list_files():
    """List uploaded files."""
    # TODO: Implement file listing from original app.py
    return jsonify({"message": "File endpoints - to be implemented"})
