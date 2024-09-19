from pathlib import Path
from setuptools import find_packages, setup


project_root = Path(__file__).parent
install_requires = [
    "coloredlogs",
    "datasets>=2.9.0",
    "flask-sse",
    "Flask>=2.2.2",
    "gunicorn",
    "json2table",
    "lxml",
    "markdown",
    "natsort",
    "openai",
    "python-slugify",
    "pyyaml",
    "requests",
    "scipy",
    "tinyhtml",
]

setup(
    name="factgenie",
    version="0.0.1",
    python_requires=">=3.8",
    description="factgenie: A Toolkit for Annotating and Visualizing LLM Hallucinations.",
    author="Zdenek Kasner, Ondrej Dusek",
    author_email="kasner@ufal.mff.cuni.cz",
    long_description=(project_root / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/kasnerz/factgenie",
    license="Apache-2.0 License",
    packages=find_packages(exclude=["test", "test.*"]),
    # package_dir={"": "src"},
    package_data={
        "factgenie": ["static/css/*", "static/img/*", "static/js/*", "templates/*"],
    },
    data_files=[("factgenie", ["factgenie/config.yml"])],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "factgenie=factgenie.cli:run",
        ],
    },
    install_requires=install_requires,
    extras_require={
        "dev": [
            "wheel",
            "black",
            "ipdb",
        ],
        "deploy": [
            "gunicorn",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Intended Audience :: Science/Research",
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
)
