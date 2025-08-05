#!/usr/bin/env python3
"""
TQ GenAI Chat - Setup script for Debian packaging
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    # Filter out comments and empty lines
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="tq-genai-chat",
    version="1.0.0",
    author="TQ GenAI Chat Team",
    author_email="dev@tqgenai.com",
    description="Multi-provider GenAI chat application with advanced file processing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/emeeran/TQ_GenAI_Chat",
    packages=find_packages(),
    py_modules=['app', 'ai_models', 'persona'],
    include_package_data=True,
    package_data={
        '': ['*.md', '*.txt', '*.json', '*.toml'],
        'static': ['*'],
        'templates': ['*'],
        'config': ['*'],
    },
    data_files=[
        ('share/tq-genai-chat', ['README.md', 'requirements.txt']),
        ('share/tq-genai-chat/templates', ['templates/index.html']),
        ('share/tq-genai-chat/static', [
            'static/script.js',
            'static/styles.css',
            'static/favicon.ico',
            'static/portrait-sketch-simple.svg',
            'static/portrait-sketch.svg'
        ]),
        ('share/applications', ['debian/tq-genai-chat.desktop']),
        ('usr/bin', ['debian/tq-genai-chat-launcher']),
        ('etc/systemd/system', ['debian/tq-genai-chat.service']),
    ],
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    python_requires=">=3.10",
    entry_points={
        'console_scripts': [
            'tq-genai-chat=app:main',
        ],
    },
)
