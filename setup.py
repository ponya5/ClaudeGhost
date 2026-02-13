#!/usr/bin/env python3
"""Setup script for ClaudeGhost."""
from pathlib import Path
from setuptools import setup, find_packages

this_directory = Path(__file__).parent
long_description = ""
readme_path = this_directory / "README.md"
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="claudeghost",
    version="2.0.0",
    description="Headless Supervisor for the Anthropic Claude CLI with Telegram notifications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ClaudeGhost Contributors",
    author_email="",
    url="https://github.com/yourusername/ClaudeGhost",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/ClaudeGhost/issues",
        "Documentation": "https://github.com/yourusername/ClaudeGhost#readme",
        "Source Code": "https://github.com/yourusername/ClaudeGhost",
    },
    keywords="claude ai automation telegram bot supervisor cli",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pexpect>=4.9.0;platform_system!='Windows'",
        "requests>=2.31.0",
        "rich>=13.7.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": ["pytest>=7.4.0"],
    },
    entry_points={
        "console_scripts": [
            "claudeghost=src.main:main",
        ],
    },
    include_package_data=True,
)
