from setuptools import setup
setup(
    name='pyfolio',    # This is the name of your PyPI-package.
    version='0.2',                          # Update the version number for new releases
    url='https://github.com/jianboli/pyfolio',                  # The name of your scipt, and also the command you'll be using for calling it
    author="Jianbo Li",
	license="MIT",
	install_requires=[
        'numpy', 
        'pandas', 
        'tia'
    ]
)
