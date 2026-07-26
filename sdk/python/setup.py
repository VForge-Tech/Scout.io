from setuptools import setup

setup(
    name="scout-sdk",
    version="0.1.0",
    packages=["scout_sdk"],
    install_requires=["httpx>=0.27.0"],
    python_requires=">=3.10",
)
