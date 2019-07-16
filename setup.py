import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()
# end with

setuptools.setup(
    name="alerter",
    version="0.1.1",
    author="Zhang Qianqian",
    author_email="sola.qq.1987@gmail.com",
    description="A really simple server to receive alert message and put to database, or send to slack",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kuanpern/alerter_server",
    packages=setuptools.find_packages(),
    install_requires=[
      'Flask>=1.1.1',
      'Jinja2>=2',
      'jupyter>=1.0.0',
      'pandas>=0.20',
      'requests>=2',
      'pymysql>=0.9.3',
      'sendgrid>=5',
      'SQLAlchemy>=1',
      'python-dotenv>=0.10.3',
      'PyYAML>=3',
      'slackclient>=2.1.0',
      'opends @ git+https://kuanpern@bitbucket.org/kuanpern/open_data_sciences.git@d48bc93993f7f41b481f3cac9a8a6684f56c83d3#egg=opends',
    ]
)