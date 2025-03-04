/**
 * Script Validator for TQ GenAI Chat
 * Checks JavaScript files for common errors and potential issues
 * Run this script with Node.js to validate JS files
 */

const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
    rootDir: path.resolve(__dirname, '..'),
    jsDir: path.resolve(__dirname, '..', 'static', 'js'),
    excludeDirs: ['node_modules', 'dist', 'vendor'],
    excludeFiles: ['script-validator.js'],
    checks: {
        duplicateDeclarations: true,
        unusedVariables: false,  // More complex, might have false positives
        syntaxErrors: true
    }
};

// ANSI color codes for terminal output
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m'
};

// Helper functions
function log(message, color = colors.reset) {
    console.log(`${color}${message}${colors.reset}`);
}

function findJsFiles(dir, fileList = []) {
    const files = fs.readdirSync(dir);

    for (const file of files) {
        const filePath = path.join(dir, file);
        const stat = fs.statSync(filePath);

        if (stat.isDirectory()) {
            if (!CONFIG.excludeDirs.includes(file)) {
                findJsFiles(filePath, fileList);
            }
        } else if (stat.isFile() &&
            path.extname(file) === '.js' &&
            !CONFIG.excludeFiles.includes(file)) {
            fileList.push(filePath);
        }
    }

    return fileList;
}

function checkDuplicateDeclarations(content, fileName) {
    const issues = [];
    const varRegex = /\b(var|let|const|function)\s+([a-zA-Z0-9_$]+)/g;
    const declarations = {};
    let match;

    // Find all declarations
    while ((match = varRegex.exec(content)) !== null) {
        const type = match[1];
        const name = match[2];
        const position = match.index;

        // Get line number for better reporting
        const lineNumber = content.substring(0, position).split('\n').length;

        if (!declarations[name]) {
            declarations[name] = [];
        }

        declarations[name].push({ type, position, lineNumber });
    }

    // Check for duplicates
    for (const [name, instances] of Object.entries(declarations)) {
        if (instances.length > 1) {
            // Check if it's in the same scope (simplified check)
            // This is a simplified approach and might have false positives
            const sameScope = instances.filter(instance => {
                return instance.type === 'var' || instance.type === 'function';
            }).length > 1;

            if (sameScope) {
                issues.push({
                    name,
                    message: `Duplicate declaration of '${name}'`,
                    instances: instances.map(i => `line ${i.lineNumber} (${i.type})`)
                });
            }
        }
    }

    return issues;
}

function checkSyntaxErrors(content, fileName) {
    const issues = [];

    try {
        // Use eval in a Function constructor to check syntax without executing
        new Function(content);
    } catch (e) {
        // Parse error message for line number and message
        const match = e.message.match(/at line (\d+)/);
        const lineNumber = match ? match[1] : 'unknown';

        issues.push({
            name: 'SyntaxError',
            message: e.message,
            instances: [`line ${lineNumber}`]
        });
    }

    return issues;
}

function validateJsFile(filePath) {
    const fileName = path.basename(filePath);
    log(`Validating ${fileName}...`, colors.blue);

    try {
        const content = fs.readFileSync(filePath, 'utf8');
        const issues = [];

        // Run configured checks
        if (CONFIG.checks.duplicateDeclarations) {
            issues.push(...checkDuplicateDeclarations(content, fileName));
        }

        if (CONFIG.checks.syntaxErrors) {
            issues.push(...checkSyntaxErrors(content, fileName));
        }

        // Report issues
        if (issues.length === 0) {
            log(`✓ No issues found in ${fileName}`, colors.green);
            return { file: fileName, valid: true, issues: [] };
        } else {
            log(`✗ Found ${issues.length} issues in ${fileName}:`, colors.red);

            issues.forEach(issue => {
                log(`  - ${issue.message}`, colors.yellow);
                issue.instances.forEach(instance => {
                    log(`    at ${instance}`, colors.yellow);
                });
            });

            return { file: fileName, valid: false, issues };
        }
    } catch (error) {
        log(`✗ Error processing ${fileName}: ${error.message}`, colors.red);
        return { file: fileName, valid: false, error: error.message };
    }
}

function fixDuplicateDeclarations(filePath) {
    try {
        let content = fs.readFileSync(filePath, 'utf8');
        const fileName = path.basename(filePath);
        const issues = checkDuplicateDeclarations(content, fileName);

        if (issues.length === 0) {
            log(`No duplicate declarations to fix in ${fileName}`, colors.green);
            return false;
        }

        log(`Attempting to fix duplicate declarations in ${fileName}...`, colors.blue);

        // Sort issues by position (descending) to prevent offset changes
        issues.sort((a, b) => {
            const aPos = Math.max(...a.instances.map(i => parseInt(i.match(/line (\d+)/)[1])));
            const bPos = Math.max(...b.instances.map(i => parseInt(i.match(/line (\d+)/)[1])));
            return bPos - aPos;
        });

        // Create a backup
        const backupPath = filePath + '.backup';
        fs.writeFileSync(backupPath, content);
        log(`Created backup at ${backupPath}`, colors.blue);

        // Simple fix: Just add a comment to second declarations
        // This is a simplistic approach; a proper fix would require a JS parser
        let lines = content.split('\n');

        for (const issue of issues) {
            const name = issue.name;
            const regex = new RegExp(`\\b(var|let|const|function)\\s+(${name})\\b`, 'g');

            let firstFound = false;
            for (let i = 0; i < lines.length; i++) {
                if (regex.test(lines[i])) {
                    if (firstFound) {
                        // Comment out or fix the duplicate declaration
                        lines[i] = lines[i].replace(regex, `/* DUPLICATE: $1 $2 */`);
                        log(`Fixed duplicate declaration of '${name}' on line ${i + 1}`, colors.green);
                    } else {
                        firstFound = true;
                    }
                    // Reset regex to start from beginning for next line
                    regex.lastIndex = 0;
                }
            }
        }

        // Write fixed content
        fs.writeFileSync(filePath, lines.join('\n'));
        log(`✓ Fixed ${issues.length} issues in ${fileName}`, colors.green);

        return true;
    } catch (error) {
        log(`✗ Error fixing ${path.basename(filePath)}: ${error.message}`, colors.red);
        return false;
    }
}

// Main function
function main() {
    log('JavaScript File Validator', colors.bright + colors.blue);
    log('-------------------------', colors.blue);

    // Find all JavaScript files
    const jsFiles = findJsFiles(CONFIG.jsDir);
    log(`Found ${jsFiles.length} JavaScript files to validate.\n`);

    // Validate each file
    const results = jsFiles.map(validateJsFile);

    // Summary
    const validCount = results.filter(r => r.valid).length;
    const issueCount = results.filter(r => !r.valid).length;

    log('\nValidation Summary:', colors.bright);
    log(`Total files: ${results.length}`, colors.reset);
    log(`Valid: ${validCount}`, colors.green);
    log(`Issues found: ${issueCount}`, issueCount > 0 ? colors.red : colors.green);

    // Ask to fix issues if found
    if (issueCount > 0) {
        log('\nWould you like to attempt to fix the issues? (y/n)', colors.yellow);
        // In a real script, you'd handle user input here
        // For demonstration, we'll assume yes for simplicity
        const fixResults = results
            .filter(r => !r.valid)
            .map(result => {
                const filePath = path.join(CONFIG.jsDir, result.file);
                return fixDuplicateDeclarations(filePath);
            });

        const fixedCount = fixResults.filter(Boolean).length;
        log(`\nFixed ${fixedCount} out of ${issueCount} files with issues.`, colors.bright);
    }

    log('\nDone!', colors.bright + colors.green);
}

// Run the script
main();

// Export functions for testing or use as a module
module.exports = {
    validateJsFile,
    checkDuplicateDeclarations,
    fixDuplicateDeclarations
};
