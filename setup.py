from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

TESTS_REQUIRE = ["selenium~=3.141", "pylint", "mock", "black", "bandit"]

setup(
    name="webviz_4d",
    description="webviz-4d",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Equinor",
    packages=find_packages(exclude=["tests"]),
    entry_points={
        "webviz_config_plugins": [
            "SurfaceViewer = webviz_4d.plugins:SurfaceViewer",
            "SurfaceViewer1 = webviz_4d.plugins:SurfaceViewer1",
            "SurfaceViewer2 = webviz_4d.plugins:SurfaceViewer2",
            "SurfaceViewer3 = webviz_4d.plugins:SurfaceViewer3",
            "SurfaceViewer4D = webviz_4d.plugins:SurfaceViewer4D",
            "SurfaceViewer4D1 = webviz_4d.plugins:SurfaceViewer4D1",
        ]
    },
    install_requires=[
        "webviz-config>=0.0.24",
        "xtgeo~=2.1",
        "pillow~=6.1",
        "webviz-subsurface-components>=0.0.3",
    ],
    tests_require=TESTS_REQUIRE,
    extras_require={"tests": TESTS_REQUIRE},
    setup_requires=["setuptools_scm~=3.2"],
    use_scm_version=True,
    zip_safe=False,
    classifiers=[
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
)
