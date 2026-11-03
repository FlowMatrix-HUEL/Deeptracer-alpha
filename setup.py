"""
实现包在全局导入
"""
from setuptools import setup,find_packages

setup(
    name="deeptracer",
    version="1.0.0",
    packages=find_packages(),
    install_requires = [
        "python-dotenv>=1.2.1",
        "objprint>=0.3.0",
        "tqdm>=4.67.1",
        "pyvis>=0.3.2",
        "networkx>=3.4.2",
        "pyinstrument>=5.1.1",
        "fastapi>=0.135.1",
        "uvicorn>=0.41.0",
        "pydantic>=2.10.0",
        "langchain>=0.3.0",
        "langgraph>=0.2.0",
        "langchain-openai>=0.3.0"
    ],
    entry_points={
        "console_scripts": [
            "deeptracer=deeptracer.clip:main",
            "deeptracer-config=deeptracer.config_cli:main",
            "deeptracer-web=deeptracer.server.app:main",
        ]
    },
    test_suite = "test"
)
