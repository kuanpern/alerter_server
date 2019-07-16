from setuptools import setup, find_packages

with open('LICENSE') as f:
    license = f.read()

with open("README.md", "r") as fh:
    long_description = fh.read()
# end with

setup(
    name='alerter_server',
    version='0.1.0',
    description='A simple server to register and send alerts periodically',
    long_description=long_description,
    author='Tan Kuan Pern',
    author_email='kptan86@gmail.com',
    long_description_content_type="text/markdown",
    url='https://.i-scube.com/',
    license=license,
    packages=find_packages(),
    include_package_data=True,
    package_data={
    },
    dependency_links=[
        'git+https://kuanpern@bitbucket.org/kuanpern/open_data_sciences.git#egg=opends',
    ],
    install_requires=[
      'Flask>=1.0',
      'mysqlclient>=1.3',
      'numpy>=1.15',
      'opends>=0.0.0',
      'PyYAML>=5.0',
      'requests>=2.20',
      'sendgrid>=5.3',
      'slackclient>=2.0',
      'SQLAlchemy>=1.2',
   ],
    entry_points = {
      'console_scripts': [
        'send_alerts_email=alerter_server.send_alerts_email.py:cli',
      ]
    },
)
