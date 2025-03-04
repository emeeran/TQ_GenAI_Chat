#!/bin/bash
# A simple script to restore the UI in case of emergencies

echo "TQ GenAI Chat UI Restoration Tool"
echo "================================="

# Navigate to the project root directory
cd "$(dirname "$0")"

# Check if the templates directory exists
if [ ! -d "./templates" ]; then
  echo "Error: templates directory not found!"
  exit 1
fi

# Function to restore index.html from backup
restore_index() {
  if [ -f "./templates/index_backup.html" ]; then
    echo "Restoring index.html from backup..."
    cp "./templates/index_backup.html" "./templates/index.html"
    echo "Restoration complete."
  else
    echo "Error: No backup file found at ./templates/index_backup.html"
    echo "Will try to use the fix_html.py script instead..."

    # Try to run the Python fix script
    if [ -f "./utils/fix_html.py" ]; then
      echo "Running HTML fix utility..."
      python3 ./utils/fix_html.py
    else
      echo "Error: fix_html.py script not found at ./utils/fix_html.py"
      echo "Manual intervention required."
    fi
  fi
}

echo "This script will attempt to restore the UI to its working state."
echo "Do you want to proceed? [y/N]"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
  restore_index
else
  echo "Operation cancelled."
fi

echo ""
echo "If the issue persists, please check the browser console for errors,"
echo "and consider manually editing the HTML template or contact support."
