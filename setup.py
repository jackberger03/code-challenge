# setup.py
from setuptools import setup, find_packages

setup(
    name="code_challenge",
    version="0.1.0",
    description="DocuSign Signing Service",
    packages=find_packages(where="."),
    python_requires=">=3.8",
    install_requires=[
        "fastapi",
        "pydantic",
        "email-validator",
        "docusign-esign",
    ],
)