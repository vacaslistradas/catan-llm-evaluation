from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="catan-llm-evaluation",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="LLM evaluation framework using Settlers of Catan gameplay",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vacaslistradas/catan-llm-evaluation",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "catan-llm-eval=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["web/templates/*.html", "web/static/css/*.css", "web/static/js/*.js"],
    },
)