"""
JavaScript Error Checker for TQ GenAI Chat
Checks JavaScript files for common errors and potential issues
"""
import os
import re
import sys
import json
from pathlib import Path
import argparse

# Configuration
CONFIG = {
    "js_dir": Path(__file__).parent.parent / "static" / "js",
    "exclude_dirs": ["node_modules", "dist", "vendor"],
    "exclude_files": ["script-validator.js"],
    "backup_dir": Path(__file__).parent.parent / "backups" / "js",
    "checks": {
        "duplicate_declarations": True,
        "syntax_errors": True,
        "missing_semicolons": True,
        "unused_variables": False,  # More complex, can have false positives
    }
}

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'

def log(message, color=Colors.RESET):
    """Print a colored message"""
    print(f"{color}{message}{Colors.RESET}")

def find_js_files(directory, file_list=None):
    """Find all JavaScript files in the directory"""
    if file_list is None:
        file_list = []

    for item in os.listdir(directory):
        path = os.path.join(directory, item)

        if os.path.isdir(path) and item not in CONFIG["exclude_dirs"]:
            find_js_files(path, file_list)
        elif os.path.isfile(path) and path.endswith(".js") and item not in CONFIG["exclude_files"]:
            file_list.append(path)

    return file_list

def check_duplicate_declarations(content, filename):
    """Check for duplicate variable declarations"""
    issues = []
    var_regex = r'\b(var|let|const|function)\s+([a-zA-Z0-9_$]+)'
    declarations = {}

    for match in re.finditer(var_regex, content):
        decl_type, name = match.groups()
        position = match.start()

        # Get line number for better reporting
        line_number = content[:position].count('\n') + 1

        if name not in declarations:
            declarations[name] = []

        declarations[name].append({
            "type": decl_type,
            "position": position,
            "line_number": line_number
        })

    # Check for duplicates
    for name, instances in declarations.items():
        if len(instances) > 1:
            # Check if it's in the same scope (simplified approach)
            # This is a basic check and might have false positives
            same_scope_declarations = [
                instance for instance in instances
                if instance["type"] == "var" or instance["type"] == "function"
            ]

            if len(same_scope_declarations) > 1:
                issues.append({
                    "name": name,
                    "message": f"Duplicate declaration of '{name}'",
                    "instances": [f"line {i['line_number']} ({i['type']})" for i in instances]
                })

    return issues

def check_missing_semicolons(content, filename):
    """Check for missing semicolons"""
    issues = []

    # This is a simplified check that might have false positives and negatives
    lines = content.splitlines()
    for i, line in enumerate(lines):
        # Skip comments and empty lines
        if re.match(r'^\s*\/\/|^\s*\/\*|^\s*\*|^\s*$', line):
            continue

        # Check if line needs a semicolon but doesn't have one
        if (re.search(r'[a-zA-Z0-9_$)\]\'"`]\s*$', line) and
            not re.search(r';\s*$', line) and
            not re.search(r'{\s*$', line) and
            not re.search(r'}\s*$', line) and
            not re.search(r'\/\/|\/\*', line)):

            # Check if next line starts with a character that would need a semicolon
            if i < len(lines) - 1 and re.match(r'\s*[\[({+\-\/`\'"]', lines[i+1]):
                issues.append({
                    "line": i + 1,
                    "message": "Possible missing semicolon",
                    "content": line.strip()
                })

    return issues

def validate_js_file(file_path):
    """Validate a JavaScript file for issues"""
    filename = os.path.basename(file_path)
    log(f"Validating {filename}...", Colors.BLUE)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        issues = []

        # Run configured checks
        if CONFIG["checks"]["duplicate_declarations"]:
            issues.extend(check_duplicate_declarations(content, filename))

        if CONFIG["checks"]["missing_semicolons"]:
            semicolon_issues = check_missing_semicolons(content, filename)
            if semicolon_issues:
                issues.append({
                    "name": "MissingSemicolons",
                    "message": "Missing semicolons detected",
                    "instances": [f"line {issue['line']}: {issue['content']}" for issue in semicolon_issues]
                })

        # Report issues
        if not issues:
            log(f"✓ No issues found in {filename}", Colors.GREEN)
            return {"file": filename, "valid": True, "issues": []}
        else:
            log(f"✗ Found {len(issues)} issues in {filename}:", Colors.RED)

            for issue in issues:
                log(f"  - {issue['message']}", Colors.YELLOW)
                for instance in issue["instances"]:
                    log(f"    at {instance}", Colors.YELLOW)

            return {"file": filename, "valid": False, "issues": issues}

    except Exception as e:
        log(f"✗ Error processing {filename}: {str(e)}", Colors.RED)
        return {"file": filename, "valid": False, "error": str(e)}

def fix_duplicate_declarations(file_path):
    """Fix duplicate declarations in a JavaScript file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        filename = os.path.basename(file_path)
        issues = check_duplicate_declarations(content, filename)

        if not issues:
            log(f"No duplicate declarations to fix in {filename}", Colors.GREEN)
            return False

        log(f"Attempting to fix duplicate declarations in {filename}...", Colors.BLUE)

        # Sort issues by line number (descending) to prevent offset changes
        issues.sort(key=lambda x: max(int(re.search(r'line (\d+)', i).group(1)) for i in x["instances"]), reverse=True)

        # Create a backup
        os.makedirs(CONFIG["backup_dir"], exist_ok=True)
        backup_path = os.path.join(CONFIG["backup_dir"], f"{filename}.backup")
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        log(f"Created backup at {backup_path}", Colors.BLUE)

        # Simple fix: Add a window or prefix variable name to avoid duplicates
        lines = content.splitlines()

        for issue in issues:
            name = issue["name"]

            # Parse line numbers from instances
            line_numbers = []
            for instance in issue["instances"]:
                match = re.search(r'line (\d+)', instance)
                if match:
                    line_numbers.append(int(match.group(1)))

            # Sort line numbers descending to avoid index shifts
            line_numbers.sort(reverse=True)

            # Skip the first occurrence
            for line_num in line_numbers[1:]:
                # Fix the line
                current_line = lines[line_num - 1]
                if "errorLog" in current_line:
                    # Special case for errorLog
                    fixed_line = current_line.replace(f"const {name}", f"/* FIXED DUPLICATE */ window.{name}")
                elif "dom" in current_line:
                    # Special case for dom
                    fixed_line = current_line.replace(f"const {name}", f"/* FIXED DUPLICATE */ window.{name}")
                elif "closeBtn" in current_line:
                    # Special case for closeBtn
                    fixed_line = current_line.replace(f"const {name}", f"/* FIXED DUPLICATE */ const {name}Button")
                else:
                    # Generic case
                    fixed_line = current_line.replace(f"var {name}", f"/* FIXED DUPLICATE */ window.{name}")
                    fixed_line = fixed_line.replace(f"let {name}", f"/* FIXED DUPLICATE */ window.{name}")
                    fixed_line = fixed_line.replace(f"const {name}", f"/* FIXED DUPLICATE */ window.{name}")
                    fixed_line = fixed_line.replace(f"function {name}", f"/* FIXED DUPLICATE */ window.{name} = function")

                lines[line_num - 1] = fixed_line
                log(f"Fixed duplicate declaration of '{name}' on line {line_num}", Colors.GREEN)

        # Write fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        log(f"✓ Fixed {len(issues)} issues in {filename}", Colors.GREEN)
        return True

    except Exception as e:
        log(f"✗ Error fixing {os.path.basename(file_path)}: {str(e)}", Colors.RED)
        return False

def main():
    parser = argparse.ArgumentParser(description="JavaScript Error Checker for TQ GenAI Chat")
    parser.add_argument('--fix', action='store_true', help="Attempt to fix issues automatically")
    parser.add_argument('--file', help="Validate a specific JavaScript file")
    args = parser.parse_args()

    log("JavaScript File Validator", Colors.BOLD + Colors.BLUE)
    log("-------------------------", Colors.BLUE)

    # Find JavaScript files
    if args.file:
        js_files = [args.file]
    else:
        js_files = find_js_files(CONFIG["js_dir"])

    log(f"Found {len(js_files)} JavaScript files to validate.\n")

    # Validate each file
    results = [validate_js_file(file) for file in js_files]

    # Summary
    valid_count = sum(1 for r in results if r["valid"])
    issue_count = sum(1 for r in results if not r["valid"])

    log("\nValidation Summary:", Colors.BOLD)
    log(f"Total files: {len(results)}", Colors.RESET)
    log(f"Valid: {valid_count}", Colors.GREEN)
    log(f"Issues found: {issue_count}", Colors.RED if issue_count > 0 else Colors.GREEN)

    # Fix issues if requested
    if args.fix and issue_count > 0:
        log("\nAttempting to fix issues...", Colors.YELLOW)
        fix_count = 0

        for result, file_path in zip(results, js_files):
            if not result["valid"]:
                if fix_duplicate_declarations(file_path):
                    fix_count += 1

        log(f"\nFixed {fix_count} out of {issue_count} files with issues.", Colors.BOLD)

    log("\nDone!", Colors.BOLD + Colors.GREEN)

    # Return error code if issues found and not fixed
    if issue_count > 0 and (not args.fix or fix_count < issue_count):
        sys.exit(1)

if __name__ == "__main__":
    main()
