/**
 * Enhanced File Uploader component
 * Handles file uploads with progress tracking, previews, and file management
 */

class FileUploader {
    constructor(options = {}) {
        this.options = {
            uploadUrl: '/upload',
            statusUrl: '/upload/status',
            documentListUrl: '/documents/list',
            documentViewUrl: '/documents/view',
            documentDeleteUrl: '/documents/delete',
            maxFileSize: 64 * 1024 * 1024, // 64MB
            allowedTypes: ['.pdf', '.docx', '.doc', '.txt', '.md', '.json', '.csv', '.jpg', '.jpeg', '.png'],
            dropZoneId: 'drop-zone',
            fileInputId: 'file-input',
            fileListId: 'file-list',
            uploadBtnId: 'upload-btn',
            maxFiles: 10,
            ...options
        };

        this.uploadQueue = [];
        this.activeUploads = 0;
        this.maxConcurrentUploads = 3;
        this.uploadedFiles = [];

        this.init();
    }

    init() {
        // Initialize DOM elements
        this.dropZone = document.getElementById(this.options.dropZoneId);
        this.fileInput = document.getElementById(this.options.fileInputId);
        this.fileList = document.getElementById(this.options.fileListId);
        this.uploadBtn = document.getElementById(this.options.uploadBtnId);

        if (!this.dropZone || !this.fileInput || !this.fileList) {
            console.error('FileUploader: Required DOM elements not found');
            return;
        }

        // Create UI notification elements
        this.createNotificationElements();

        // Set up event listeners
        this.setupEventListeners();

        // Load existing documents
        this.loadDocumentList();
    }

    createNotificationElements() {
        // Create error message element
        this.errorMessage = document.createElement('div');
        this.errorMessage.className = 'error-message';
        document.body.appendChild(this.errorMessage);

        // Create info message element
        this.infoMessage = document.createElement('div');
        this.infoMessage.className = 'info-message';
        document.body.appendChild(this.infoMessage);
    }

    setupEventListeners() {
        // File input change
        this.fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files);
        });

        // Drag and drop
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('dragover');
        });

        this.dropZone.addEventListener('dragleave', () => {
            this.dropZone.classList.remove('dragover');
        });

        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('dragover');
            this.handleFileSelect(e.dataTransfer.files);
        });

        // Upload button
        if (this.uploadBtn) {
            this.uploadBtn.addEventListener('click', () => {
                this.processQueue();
            });
        }

        // Document actions (delete, view) using event delegation
        this.fileList.addEventListener('click', (e) => {
            const target = e.target;

            // Handle delete action
            if (target.classList.contains('delete-btn')) {
                const filename = target.dataset.filename;
                this.deleteDocument(filename);
            }

            // Handle view action
            if (target.classList.contains('view-btn')) {
                const filename = target.dataset.filename;
                this.viewDocument(filename);
            }
        });
    }

    handleFileSelect(fileList) {
        // Check number of files
        if (fileList.length > this.options.maxFiles) {
            this.showError(`Too many files selected. Maximum allowed is ${this.options.maxFiles}`);
            return;
        }

        // Process each file
        for (const file of fileList) {
            // Check file size
            if (file.size > this.options.maxFileSize) {
                this.showError(`File "${file.name}" is too large. Maximum size is ${this.formatFileSize(this.options.maxFileSize)}`);
                continue;
            }

            // Check file type
            const fileExt = this.getFileExtension(file.name);
            if (!this.options.allowedTypes.includes(fileExt)) {
                this.showError(`File type "${fileExt}" is not allowed`);
                continue;
            }

            // Add to upload queue
            this.uploadQueue.push(file);

            // Add to UI
            this.addFileToUI(file);
        }

        // Clear the file input
        this.fileInput.value = '';

        // Process queue automatically if no button
        if (!this.uploadBtn) {
            this.processQueue();
        }
    }

    addFileToUI(file) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.dataset.filename = file.name;

        const fileIcon = this.getFileIcon(file.name);

        fileItem.innerHTML = `
            <div class="file-info">
                <div class="file-icon">${fileIcon}</div>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${this.formatFileSize(file.size)}</div>
                </div>
            </div>
            <div class="file-progress">
                <div class="progress-bar" style="width: 0%"></div>
                <div class="progress-text">Queued</div>
            </div>
            <div class="file-actions">
                <button class="remove-btn" data-filename="${file.name}">✕</button>
            </div>
        `;

        // Add remove button functionality
        fileItem.querySelector('.remove-btn').addEventListener('click', () => {
            this.removeFileFromQueue(file.name);
            fileItem.remove();
        });

        this.fileList.appendChild(fileItem);
    }

    processQueue() {
        if (this.uploadQueue.length === 0 || this.activeUploads >= this.maxConcurrentUploads) {
            return;
        }

        // Process up to maxConcurrentUploads
        while (this.uploadQueue.length > 0 && this.activeUploads < this.maxConcurrentUploads) {
            const file = this.uploadQueue.shift();
            this.uploadFile(file);
        }
    }

    async uploadFile(file) {
        this.activeUploads++;

        try {
            // Update UI to show upload started
            const fileItem = this.fileList.querySelector(`.file-item[data-filename="${file.name}"]`);
            if (!fileItem) {
                this.activeUploads--;
                return;
            }

            const progressBar = fileItem.querySelector('.progress-bar');
            const progressText = fileItem.querySelector('.progress-text');
            progressText.textContent = 'Uploading (0%)';

            // Create FormData
            const formData = new FormData();
            formData.append('files[]', file);

            // Upload with progress tracking
            const response = await this.uploadWithProgress(formData, (percent) => {
                progressBar.style.width = `${percent}%`;
                progressText.textContent = `Uploading (${percent}%)`;
            });

            // Check response
            if (response.status === 'success') {
                // Add to uploaded files
                const fileInfo = response.results.find(r => r.filename === file.name);

                if (fileInfo && fileInfo.status === 'success') {
                    this.uploadedFiles.push({
                        filename: file.name,
                        size: fileInfo.size || file.size,
                        timestamp: new Date().toISOString()
                    });

                    // Update UI to show success
                    fileItem.classList.add('uploaded');
                    progressBar.style.width = '100%';
                    progressText.textContent = 'Uploaded';

                    // Replace actions with view and delete buttons
                    const actionsDiv = fileItem.querySelector('.file-actions');
                    actionsDiv.innerHTML = `
                        <button class="view-btn" data-filename="${file.name}">View</button>
                        <button class="delete-btn" data-filename="${file.name}">Delete</button>
                    `;

                    this.showInfo(`File "${file.name}" uploaded successfully`);

                    // Poll for document list update
                    this.pollForDocumentListUpdate(5);
                } else {
                    // Handle partial success (one file failed)
                    const errorMsg = fileInfo ? fileInfo.error : 'Unknown error';
                    this.handleUploadError(file.name, errorMsg);
                }
            } else {
                // Handle server error
                const errorMsg = response.error || 'Server error during upload';
                this.handleUploadError(file.name, errorMsg);
            }
        } catch (error) {
            // Handle network or other errors
            this.handleUploadError(file.name, error.message);
        } finally {
            this.activeUploads--;

            // Process next files in queue
            if (this.uploadQueue.length > 0) {
                this.processQueue();
            }
        }
    }

    handleUploadError(filename, errorMessage) {
        const fileItem = this.fileList.querySelector(`.file-item[data-filename="${filename}"]`);
        if (!fileItem) return;

        // Mark as error in UI
        fileItem.classList.add('error');
        const progressText = fileItem.querySelector('.progress-text');
        progressText.textContent = 'Failed';

        // Replace actions with retry and remove buttons
        const actionsDiv = fileItem.querySelector('.file-actions');
        actionsDiv.innerHTML = `
            <button class="retry-btn" data-filename="${filename}">Retry</button>
            <button class="remove-btn" data-filename="${filename}">Remove</button>
        `;

        // Add retry functionality
        fileItem.querySelector('.retry-btn').addEventListener('click', () => {
            // Find the original file and re-add to queue
            const originalFile = this.findOriginalFile(filename);
            if (originalFile) {
                this.uploadQueue.push(originalFile);

                // Reset UI
                fileItem.classList.remove('error');
                const progressBar = fileItem.querySelector('.progress-bar');
                progressBar.style.width = '0%';
                progressText.textContent = 'Queued';

                // Replace actions
                actionsDiv.innerHTML = `
                    <button class="remove-btn" data-filename="${filename}">✕</button>
                `;

                // Start upload if possible
                this.processQueue();
            } else {
                this.showError(`Cannot retry "${filename}". Please re-select the file.`);
                fileItem.remove();
            }
        });

        // Show error message
        this.showError(`Failed to upload "${filename}": ${errorMessage}`);
    }

    uploadWithProgress(formData, progressCallback) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Set up progress monitoring
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const percent = Math.round((event.loaded / event.total) * 100);
                    progressCallback(percent);
                }
            });

            // Handle completion
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (e) {
                        reject(new Error('Invalid server response'));
                    }
                } else {
                    let errorMessage = `Server error: ${xhr.status}`;
                    try {
                        const response = JSON.parse(xhr.responseText);
                        errorMessage = response.error || errorMessage;
                    } catch (e) {
                        // Use default error message
                    }
                    reject(new Error(errorMessage));
                }
            });

            // Handle errors
            xhr.addEventListener('error', () => {
                reject(new Error('Network error during upload'));
            });

            xhr.addEventListener('abort', () => {
                reject(new Error('Upload aborted'));
            });

            // Send the request
            xhr.open('POST', this.options.uploadUrl);
            xhr.send(formData);
        });
    }

    removeFileFromQueue(filename) {
        // Remove from queue
        this.uploadQueue = this.uploadQueue.filter(file => file.name !== filename);
    }

    findOriginalFile(filename) {
        // This would need to store original files somewhere
        // Currently not implemented since FileList objects are read-only
        return null;
    }

    loadDocumentList() {
        // Fetch existing documents from server
        fetch(this.options.documentListUrl)
            .then(response => response.json())
            .then(data => {
                // Clear existing files (except queued uploads)
                const existingFiles = this.fileList.querySelectorAll('.file-item.uploaded');
                existingFiles.forEach(el => el.remove());

                // Add fetched documents to UI
                const documents = data.documents || [];
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
    }

    addExistingDocumentToUI(doc) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item uploaded';
        fileItem.dataset.filename = doc.filename;

        const fileIcon = this.getFileIcon(doc.filename);
        const timestamp = doc.timestamp ? new Date(doc.timestamp).toLocaleString() : 'Unknown date';

        fileItem.innerHTML = `
            <div class="file-info">
                <div class="file-icon">${fileIcon}</div>
                <div class="file-details">
                    <div class="file-name">${doc.filename}</div>
                    <div class="file-meta">
                        <span class="file-size">${this.formatFileSize(doc.size || 0)}</span>
                        <span class="file-date">${timestamp}</span>
                    </div>
                </div>
            </div>
            <div class="file-progress">
                <div class="progress-bar" style="width: 100%"></div>
                <div class="progress-text">Uploaded</div>
            </div>
            <div class="file-actions">
                <button class="view-btn" data-filename="${doc.filename}">View</button>
                <button class="delete-btn" data-filename="${doc.filename}">Delete</button>
            </div>
        `;

        this.fileList.appendChild(fileItem);
    }

    viewDocument(filename) {
        // Call the view endpoint
        fetch(`${this.options.documentViewUrl}/${encodeURIComponent(filename)}`)
            .then(response => response.json())
            .then(data => {
                // Emit a custom event that the document viewer can listen for
                const event = new CustomEvent('document-view', {
                    detail: {
                        filename,
                        content: data.content,
                        timestamp: data.timestamp
                    }
                });
                document.dispatchEvent(event);

                // Update document preview section if it exists
                const previewDiv = document.getElementById('document-content');
                if (previewDiv && data.content) {
                    // Create a formatted preview with syntax highlighting or formatting
                    const ext = filename.split('.').pop().toLowerCase();
                    let contentHtml;

                    if (['md', 'markdown'].includes(ext)) {
                        // For markdown files, render as markdown
                        contentHtml = `<div class="markdown-content">${this.markdownToHtml(data.content)}</div>`;
                    } else if (['json'].includes(ext)) {
                        // For JSON files, format with syntax highlighting
                        contentHtml = `<pre class="code-block json">${this.syntaxHighlight(data.content)}</pre>`;
                    } else {
                        // For other text files, preserve formatting
                        contentHtml = `<pre class="text-content">${this.escapeHtml(data.content)}</pre>`;
                    }

                    previewDiv.innerHTML = `
                        <div class="document-header">
                            <h4>${filename}</h4>
                            <div class="document-meta">
                                <span class="timestamp">Uploaded: ${new Date(data.timestamp).toLocaleString()}</span>
                            </div>
                        </div>
                        <div class="document-body">
                            ${contentHtml}
                        </div>
                    `;
                }
            })
            .catch(error => {
                this.showError(`Error viewing document: ${error.message}`);
            });
    }

    deleteDocument(filename) {
        // Confirm deletion
        if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
            return;
        }

        // Call the delete endpoint
        fetch(`${this.options.documentDeleteUrl}/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Remove from UI
                    const fileItem = this.fileList.querySelector(`.file-item[data-filename="${filename}"]`);
                    if (fileItem) {
                        fileItem.remove();
                    }

                    // Show success message
                    this.showInfo(`Document "${filename}" deleted successfully`);

                    // Refresh document list to update stats
                    this.loadDocumentList();
                } else {
                    // Show error
                    throw new Error(data.error || 'Failed to delete document');
                }
            })
            .catch(error => {
                this.showError(`Error deleting document: ${error.message}`);
            });
    }

    // Utility functions

    getFileExtension(filename) {
        return '.' + filename.split('.').pop().toLowerCase();
    }

    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();

        // Return appropriate icon based on file type
        switch (ext) {
            case 'pdf':
                return '<i class="fas fa-file-pdf"></i>';
            case 'docx':
            case 'doc':
                return '<i class="fas fa-file-word"></i>';
            case 'xlsx':
            case 'xls':
            case 'csv':
                return '<i class="fas fa-file-excel"></i>';
            case 'jpg':
            case 'jpeg':
            case 'png':
            case 'gif':
                return '<i class="fas fa-file-image"></i>';
            case 'md':
            case 'markdown':
                return '<i class="fas fa-file-alt"></i>';
            case 'json':
                return '<i class="fas fa-file-code"></i>';
            default:
                return '<i class="fas fa-file"></i>';
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    showError(message, duration = 5000) {
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';

        setTimeout(() => {
            this.errorMessage.style.display = 'none';
        }, duration);
    }

    showInfo(message, duration = 3000) {
        this.infoMessage.textContent = message;
        this.infoMessage.style.display = 'block';

        setTimeout(() => {
            this.infoMessage.style.display = 'none';
        }, duration);
    }

    escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    syntaxHighlight(json) {
        if (typeof json !== 'string') {
            json = JSON.stringify(json, null, 2);
        }
        return this.escapeHtml(json);
    }

    markdownToHtml(markdown) {
        // This is a basic implementation - for production, use a proper markdown library
        // Convert headers
        let html = markdown
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            // Convert code blocks
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            // Convert inline code
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Convert bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Convert italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Convert lists
            .replace(/^\* (.*$)/gm, '<ul><li>$1</li></ul>')
            .replace(/^\d\. (.*$)/gm, '<ol><li>$1</li></ol>')
            // Fix lists (remove duplicate tags)
            .replace(/<\/ul><ul>/g, '')
            .replace(/<\/ol><ol>/g, '')
            // Convert line breaks
            .replace(/\n/gm, '<br>');

        return html;
    }

    pollForDocumentListUpdate(maxAttempts = 5) {
        let attempts = 0;

        const checkForUpdates = () => {
            attempts++;
            console.log(`Polling for document updates (attempt ${attempts}/${maxAttempts})`);

            // Force cache bypass by adding timestamp
            const timestamp = new Date().getTime();
            const url = `${this.options.documentListUrl}?t=${timestamp}`;

            fetch(url, { cache: 'no-store' })
                .then(response => response.json())
                .then(data => {
                    console.log(`Retrieved ${data.documents?.length || 0} documents`);
                    this.loadDocumentList();

                    // If we have documents or reached max attempts, stop polling
                    if ((data.documents && data.documents.length > 0) || attempts >= maxAttempts) {
                        console.log("Document list updated or max attempts reached");
                    } else {
                        // Try again after a delay
                        setTimeout(checkForUpdates, 1000);
                    }
                })
                .catch(error => {
                    console.error('Error checking document updates:', error);
                    if (attempts < maxAttempts) {
                        setTimeout(checkForUpdates, 1000);
                    }
                });
        };

        // Start polling
        setTimeout(checkForUpdates, 500);
    }
}

// Export the class for use in other modules
if (typeof module !== 'undefined') {
    module.exports = FileUploader;
}