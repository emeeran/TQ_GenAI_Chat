/**
 * Fix for the file uploader UI
 * This script should be included after the main file-uploader.js
 */

// Enhance the loadDocumentList method to force refresh
if (typeof FileUploader !== 'undefined') {
    // Keep reference to original method
    const originalLoadDocumentList = FileUploader.prototype.loadDocumentList;

    // Override with enhanced version
    FileUploader.prototype.loadDocumentList = function () {
        console.log("Enhanced loadDocumentList called");

        // Force cache bypass by adding timestamp
        const timestamp = new Date().getTime();
        const url = `${this.options.documentListUrl}?t=${timestamp}`;

        // Use fetch with cache: 'no-store' to force fresh data
        fetch(url, { cache: 'no-store' })
            .then(response => {
                console.log("Document list response status:", response.status);
                return response.json();
            })
            .then(data => {
                console.log("Document list data:", data);

                // Clear existing files (except queued uploads)
                const existingFiles = this.fileList.querySelectorAll('.file-item.uploaded');
                existingFiles.forEach(el => el.remove());

                // Add fetched documents to UI
                const documents = data.documents || [];
                console.log(`Adding ${documents.length} documents to UI`);
                documents.forEach(doc => {
                    this.addExistingDocumentToUI(doc);
                });

                // Update document stats if possible
                if (data.stats) {
                    const statsElem = document.getElementById('doc-count');
                    if (statsElem) {
                        statsElem.textContent = `${data.stats.total_documents || 0} documents`;
                    }

                    const sizeElem = document.getElementById('total-size');
                    if (sizeElem) {
                        sizeElem.textContent = this.formatFileSize(data.stats.total_size || 0);
                    }
                }
            })
            .catch(error => {
                console.error('Error loading documents:', error);
            });
    };

    // Also enhance the uploadFile method to immediately reload the list
    const originalUploadFile = FileUploader.prototype.uploadFile;

    FileUploader.prototype.uploadFile = async function (file) {
        try {
            await originalUploadFile.call(this, file);

            // Force reload document list after file upload completes
            setTimeout(() => {
                console.log("Reloading document list after upload");
                this.loadDocumentList();
            }, 500); // Small delay to ensure server processing is complete
        } catch (error) {
            console.error("Error in enhanced uploadFile:", error);
        }
    };

    console.log("FileUploader enhanced with better document listing");
}
