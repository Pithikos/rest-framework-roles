import os
import sys

try:
    from setuptools import setup
    from setuptools.command.install import install
except ImportError:
    from distutils.core import setup
    from distutils.command.install import install


VERSION = '0.2.1'


class VerifyVersionCommand(install):
    """ Custom command to verify that the git tag matches our version """
    description = 'verify that the git tag matches our version'

    def run(self):
        tag = os.getenv('CIRCLE_TAG')
        if not tag:
            sys.exit("Missing environment variable 'CIRCLE_TAG'")
        if tag != VERSION:
            sys.exit(f"Git tag: {tag} does not match the version of this app: {VERSION}")


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
    python_requires='>=3',
    keywords=[
        'permissions',
        'roles',
    ],
    classifiers=[
        'Framework :: Django',
        'Topic :: Security',
    ],
    cmdclass={
        'verify': VerifyVersionCommand,
    },
)
