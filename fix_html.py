"""
Utility script to fix malformed script tags in index.html
"""
import re

def fix_html_file(filepath):
    """
    Fix malformed script tags in the HTML file.
    """
    try:
        # Read the current content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Fix malformed script tags by finding the body end and replacing scripts
        script_section_pattern = r'(<script src=".*?)(">.*?)(<\/body>\s*<\/html>)'
        script_tags = re.findall(r'<script src="(.*?)"', content)

        # Find where body ends
        body_end_pos = content.find('</body>')
        if body_end_pos == -1:
            print("Could not find </body> tag")
            return

        # Take content up to the first script tag or body end
        first_script_pos = content.find('<script src=')
        if first_script_pos == -1 or first_script_pos > body_end_pos:
            print("No script tags found before body end")
            return

        clean_content = content[:first_script_pos]

        # Add clean script tags
        for script_src in script_tags:
            if script_src:  # Ignore empty sources
                clean_content += f'    <script src="{script_src}"></script>\n'

        # Add closing tags
        clean_content += '</body>\n</html>\n'

        # Write the fixed content back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(clean_content)

        print(f"Successfully fixed {filepath}")

    except Exception as e:
        print(f"Error fixing HTML file: {e}")

if __name__ == "__main__":
    fix_html_file('/home/em/code/wip/TQ_GenAI_Chat/templates/index.html')
