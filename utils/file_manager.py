# ...existing imports...

class FileProcessor:
    """Unified file processor with optimized handling"""

    @classmethod
    async def process_file(cls, file, filename: str) -> str:
        """Process file with improved error handling and checkpoints"""
        try:
            current_app.logger.info(f"Starting processing of file: {filename}")
            status_tracker.start_processing(filename)

            if not file or not file.filename:
                raise ProcessingError("Invalid file")

            ext = filename.rsplit('.', 1)[1].lower()
            processor = cls.get_processor(ext)

            if not processor:
                raise ProcessingError(f'Unsupported file type: {ext}')

            # Read content with size check
            content = file.read()
            if not content:
                raise ProcessingError("Empty file content")

            current_app.logger.debug(f"Processing {len(content)} bytes for {filename}")

            # Process with checkpoints
            try:
                result = await processor(
                    content,
                    progress_callback=lambda p: status_tracker.update_progress(filename, p)
                )

                if not result:
                    raise ProcessingError("Processing resulted in empty content")

                current_app.logger.info(f"Successfully processed {filename}")
                status_tracker.update_progress(filename, 100)
                return result

            except Exception as e:
                current_app.logger.error(f"Processing error for {filename}: {str(e)}")
                raise ProcessingError(f"Processing error: {str(e)}")

        except Exception as e:
            current_app.logger.error(f"File processing failed for {filename}: {str(e)}")
            status_tracker.set_error(filename, e)
            raise
