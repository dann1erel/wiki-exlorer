from setuptools import setup, find_packages

setup(
    name="wiki-explorer-ds",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "rich>=10.0.0",
        "networkx>=2.6.0",
        "matplotlib>=3.3.0",
    ],
    entry_points={
        "console_scripts": [
            "wiki-explorer-ds = wiki_explorer.cli:main",
        ],
    },
    python_requires=">=3.8",
)