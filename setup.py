from setuptools import setup
setup(
    name='pyfolio-script',    # This is the name of your PyPI-package.
    version='0.1',                          # Update the version number for new releases
    scripts=['pyfolio'],                  # The name of your scipt, and also the command you'll be using for calling it
    install_requires=[
        numpy, pandas, tia
    ]
)
