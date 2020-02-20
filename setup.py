from distutils.core import setup

VERSION = '0.2.0'

setup(
    name='rest_framework_roles',
    version=VERSION,
    description='Role-based permissions for Django REST Framework and vanilla Django.',
    author='Johan Hanssen Seferidis',
    author_email='manossef@gmail.com',
    packages=['rest_framework_roles'],
    url='https://pypi.org/project/rest-framework-roles/',
    license='LICENSE',
    long_description=open('README.md').read(),
    install_requires=[],
    keywords=[
        'permissions',
        'roles',
    ],
    classifiers=[
        'Framework :: Django',
        'Topic :: Security',
    ],
)
