from pathlib import Path

from setuptools import setup

setup(
    name="deepl-free",
    version="1.0.0",
    description="Translate text and documents via DeepL with requests, no login or API key",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="Ahmed Negm",
    license="MIT",
    url="https://github.com/x7007x/deepl-free",
    project_urls={
        "Homepage": "https://github.com/x7007x/deepl-free",
        "Repository": "https://github.com/x7007x/deepl-free",
        "Bug Tracker": "https://github.com/x7007x/deepl-free/issues",
    },
    keywords=["deepl", "translate", "translation", "translator", "documents"],
    packages=["deepl_free"],
    install_requires=["requests"],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Linguistic",
    ],
)
