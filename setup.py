# -*- coding: utf-8 -*-
"""
4d4y CLI - Setup configuration
A BBS-style terminal client for 4d4y forum.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="4d4y_cli",
    version="0.1.0",
    author="4d4y_cli contributors",
    author_email="",
    description="A BBS-style CLI client for 4d4y forum",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GreenSkinMonster/4d4y_cli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: BBS",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
    ],
    entry_points={
        "console_scripts": [
            "4d4y=forzd4y.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "forzd4y": ["py.typed"],
    },
)
