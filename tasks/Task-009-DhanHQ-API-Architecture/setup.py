#!/usr/bin/env python3
"""
DhanHQ Copy Trading System - Setup Configuration
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = (this_directory / "requirements.txt").read_text().splitlines()
requirements = [r.strip() for r in requirements if r.strip() and not r.startswith('#')]

dev_requirements = (this_directory / "requirements-dev.txt").read_text().splitlines()
dev_requirements = [r.strip() for r in dev_requirements if r.strip() and not r.startswith('#')]

setup(
    name="dhan-copy-trading",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Production-ready copy trading system for DhanHQ v2 API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/dhan-copy-trading",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "test": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "dhan-copy-trading=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.sql", "*.md"],
    },
    keywords="trading dhan copy-trading algorithmic-trading stock-market",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/dhan-copy-trading/issues",
        "Source": "https://github.com/yourusername/dhan-copy-trading",
        "Documentation": "https://github.com/yourusername/dhan-copy-trading#readme",
    },
)

