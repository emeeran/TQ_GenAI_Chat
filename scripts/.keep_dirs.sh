#!/bin/bash
# Create .gitkeep files to preserve directory structure

mkdir -p uploads saved_chats exports
touch uploads/.gitkeep
touch saved_chats/.gitkeep
touch exports/.gitkeep

echo "✅ Created .gitkeep files in:"
echo "   - uploads/"
echo "   - saved_chats/"
echo "   - exports/"
