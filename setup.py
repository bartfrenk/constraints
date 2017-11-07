from setuptools import setup

version = '0.2.3'
github = 'https://github.com/bartfrenk/constraints'

setup(
    name='constraints',
    packages=['constraints'],
    version=version,
    description='Generate validators from SQLAlchemy models',
    author='Bart Frenk',
    author_email='bart.frenk@gmail.com',
    url=github,
    download_url=github + '/{}.tar.gz'.format(version),
    keywords=['validation', 'sqlalchemy'],
    classifiers=[],
)
