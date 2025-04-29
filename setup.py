from setuptools import setup, find_packages

setup(
    name="zhouatie-cao",
    version="1.0.9",
    description="一个捕获终端错误并使用 AI 分析的命令行工具",
    author="zhouatie",
    author_email="zhouatie@gmail.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "cao=zhouatie_cao:main",
        ],
    },
    install_requires=[
        "requests>=2.25.0",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
