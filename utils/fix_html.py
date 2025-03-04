"""
Utility script to fix malformed HTML in the index.html file.
"""
import os
import re

def fix_index_html():
    """Fix the index.html file in case it becomes malformed."""
    # Get the path to the templates directory
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    index_path = os.path.join(templates_dir, 'index.html')

    if not os.path.exists(index_path):
        print(f"Error: Index file not found at {index_path}")
        return

    print(f"Attempting to fix {index_path}...")

    try:
        # Read the current content
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if the file appears to be malformed
        duplicate_tags = re.findall(r'<body>.*<body>|</body>.*</body>|</html>.*</html>', content, re.DOTALL)
        malformed_script_tags = re.findall(r'<script[^>]*>.*?</script>[^<]*?ript>', content, re.DOTALL)

        if not (duplicate_tags or malformed_script_tags):
            print("No obvious malformation detected in the HTML file.")
            return

        print("Malformed HTML detected. Attempting to restore from backup or template...")

        # Path to backup file
        backup_path = os.path.join(templates_dir, 'index_backup.html')

        # Check if we have a backup
        if os.path.exists(backup_path):
            print(f"Restoring from backup: {backup_path}")
            with open(backup_path, 'r', encoding='utf-8') as f:
                fixed_content = f.read()
        else:
            # If no backup, create a clean version with the essential structure
            print("No backup found. Creating clean version with essential structure...")
            fixed_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TQ GenAI Chat</title>
    <script src="/static/js/error-capture.js"></script>
    <script src="/static/js/dom-utilities.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="stylesheet" href="/static/styles/modern.css">
    <link rel="stylesheet" href="/static/styles/interactions.css">
    <link rel="stylesheet" href="/static/styles/components.css">
    <link rel="stylesheet" href="/static/styles/file-uploader.css">
    <link rel="stylesheet" href="/static/styles/sidebar-improvements.css">
    <link rel="stylesheet" href="/static/styles/error-handling.css">
    <link rel="stylesheet" href="/static/styles/retry-modal.css">
</head>
<body>
    <!-- Main content would go here -->
    <script src="/static/js/error-capture.js"></script>
    <script src="/static/js/dom-utilities.js"></script>
    <script src="/static/js/error-handler.js"></script>
    <script src="/static/js/modal-manager.js"></script>
    <script src="/static/js/keyboard-shortcuts.js"></script>
    <script src="/static/js/accessibility.js"></script>
    <script src="/static/js/notification-system.js"></script>
    <script src="/static/js/loading-indicators.js"></script>
    <script src="/static/js/api-diagnostics.js"></script>
    <script src="/static/js/chat-debug.js"></script>
    <script src="/static/js/chat-enhancements.js"></script>
    <script src="/static/js/chat-client.js"></script>
    <script src="/static/js/file-uploader.js"></script>
    <script src="/static/js/ui-preferences.js"></script>
    <script src="/static/js/modern-ui.js"></script>
    <script src="/static/js/sidebar.js"></script>
</body>
</html>"""

        # Create a backup of the current file first
        backup_name = f"index_malformed_{os.path.getmtime(index_path):.0f}.html"
        backup_path = os.path.join(templates_dir, backup_name)
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Created backup of malformed file: {backup_path}")

        # Write the fixed content
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        print(f"Successfully fixed {index_path}")

    except Exception as e:
        print(f"Error fixing HTML file: {e}")

# Create a backup of the current index.html file
def backup_index_html():
    """Create a backup of the current index.html file."""
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    index_path = os.path.join(templates_dir, 'index.html')
    backup_path = os.path.join(templates_dir, 'index_backup.html')

    if not os.path.exists(index_path):
        print(f"Error: Index file not found at {index_path}")
        return

    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()

        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"Successfully created backup: {backup_path}")

    except Exception as e:
        print(f"Error creating backup: {e}")

if __name__ == "__main__":
    # Uncomment the one you need
    # backup_index_html()  # To create a backup
    fix_index_html()      # To fix malformed HTML
