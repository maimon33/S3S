########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from setuptools import setup

setup(
    name='s3s',
    version='0.1.1',
    author='Assi Maimon',
    author_email='maimon33@gmail.com',
    license='LICENSE',
    description='A Simple S3 upload tool',
    entry_points={
        'console_scripts': ['s3s = s3s:_s3s']
    },
    install_requires=[
        'boto3==1.4.4',
        'click==6.6',
    ]
)