# ...existing imports...

class FileStatus:
    """File processing status tracker"""
    def __init__(self):
        self.status = {}
        self.errors = {}

    def start_processing(self, filename: str):
        self.status[filename] = {
            'status': 'processing',
            'progress': 0,
            'timestamp': datetime.now().isoformat(),
            'recoverable': True
        }

    def update_progress(self, filename: str, progress: int):
        if filename in self.status:
            self.status[filename].update({
                'progress': progress,
                'status': 'complete' if progress >= 100 else 'processing'
            })

    def set_error(self, filename: str, error: Exception, recoverable: bool = True):
        self.errors[filename] = {
            'error': str(error),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }
        if filename in self.status:
            self.status[filename].update({
                'status': 'error',
                'progress': 0,
                'recoverable': recoverable
            })

    def get_status(self, filename: str) -> Dict:
        if filename not in self.status:
            raise FileNotFoundError(f'No status found for: {filename}')

        status = self.status[filename]
        error = self.errors.get(filename)

        return {
            'status': status['status'],
            'progress': status['progress'],
            'recoverable': status.get('recoverable', False),
            'error': error['error'] if error else None,
            'timestamp': error['timestamp'] if error else status['timestamp']
        }

# Initialize global status tracker
status_tracker = FileStatus()

class FileProcessor:
    """Unified file processor with optimized handling"""

    # ...existing FileProcessor code...

    @classmethod
    async def process_file(cls, file, filename: str) -> str:
        """Process file with status tracking"""
        try:
            status_tracker.start_processing(filename)
            ext = filename.rsplit('.', 1)[1].lower()
            processor = cls.get_processor(ext)

            if not processor:
                raise ProcessingError(f'Unsupported file type: {ext}')

            content = await processor(
                file.read(),
                progress_callback=lambda p: status_tracker.update_progress(filename, p)
            )

            status_tracker.update_progress(filename, 100)
            return content

        except Exception as e:
            status_tracker.set_error(filename, e)
            raise

    # ...rest of existing code...
