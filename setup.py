from setuptools import setup, find_packages

setup(
    name="throttleros",
    version="1.0.0",
    description="Localhost Process Throttler & Shortest-Job-First Priority Scheduler",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn>=0.28.0",
        "psutil>=5.9.8",
    ],
    entry_points={
        "console_scripts": [
            "throttleros=backend.main:run_cli",
            "sysmin=backend.main:run_cli",
        ],
    },
    python_requires=">=3.10",
)
