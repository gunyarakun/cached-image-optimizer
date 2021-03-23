import setuptools

with open("README.md", "r", encoding="utf8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cached-image-optimizer",
    version="0.0.1",
    install_requires=[
        "requests>=2.25.1",
        "ratelimit>=2.2.1",
        "Pillow>=8.1.0",
    ],
    extras_require={
        "s3": ["boto3>=1.17.17"],
    },
    setup_requires=["pytest-runner>=5.3.0"],
    tests_require=[
        "pytest>=6.2.2",
        "pytest-cov>=2.11.1",
        "pytest-mock>=3.5.1",
        "requests-mock>=1.8.0",
    ],
    author="Tasuku SUENAGA a.k.a. gunyarakun",
    author_email="tasuku-s-github@titech.ac",
    description="cached image optimizer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gunyarakun/cached-image-optimizer",
    package_dir={"": "src"},
    packages=setuptools.find_packages("src"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
