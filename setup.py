from setuptools import setup, find_packages

setup(
    name="finance-chatbot",
    version="0.1.0",
    description="AI-powered finance chatbot for financial report analysis",
    author="nghiauet",
    author_email="nghiauet@local",
    packages=find_packages(where="src"),
    package_dir={"": "."},
    python_requires=">=3.8",
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "google-genai",
        "langchain",
        "transformers",
        "sentence-transformers",
        "faiss-cpu",
        "loguru"
    ],
    extras_require={
        "dev": [
            "pytest",
            "black",
            "flake8",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)