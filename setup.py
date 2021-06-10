from setuptools import setup, find_packages


INSTALL_REQUIRES = [
   'sanic',
]

setup(
    name='sanic_routes',
    version='1.0.14',
    description='API Route Schema for Sanic.',
    long_description='Generate routes and validate parameters from a JSON schema.',
    license='GPL 3.0',
    author='Elis',
    author_email='open@elis.cc',
    keywords='sanic, routes, api, schema, json',
    install_requires=INSTALL_REQUIRES,
    include_package_data=True,
    zip_safe=False,
	packages=find_packages(),
)