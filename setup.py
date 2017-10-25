from setuptools import setup

setup(
    name='s3s',
    version='0.1.1',
    author='Assi Maimon',
    author_email='maimon33@gmail.com',
    py_modules=['s3s'],
    description='A Simple S3 upload tool',
    entry_points={
        'console_scripts': [
                's3s=s3s:_s3s',
        ],
    },
    install_requires=[
        'boto3==1.4.4',
        'click==6.6',
    ]
)
