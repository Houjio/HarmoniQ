from setuptools import setup, find_packages

setup(
    name="harmoniq",
    packages=find_packages(),
    version="0.1.0",
    install_requires=[
        "pvlib",
        "pandas",
        "numpy",
        "matplotlib",
    ],
)
