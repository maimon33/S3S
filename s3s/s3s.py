import os
import json

import click

from click_didyoumean import DYMGroup

CONFIG_PATH = '{0}/s3s-config.json'.format(os.getenv("HOME"))

with open(CONFIG_PATH) as config_file:
    cfg = json.load(config_file)["s3s"]

def _send_mail(subject, msg):
    if cfg["enable_mailer"]:
        import smtplib

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(cfg["mailer_username"], cfg["mailer_password"])

        server.sendmail(cfg["mailer_from"], cfg["mailer_to"],
                        'Subject: {}\n\n{}'.format(subject, msg))
        server.quit()
    else:
        pass


class s3Client(object):
    ACCESS_KEY = os.environ.get['AWS_ACCESS_KEY_ID']
    SECRET_KEY = os.environ.get['AWS_SECRET_ACCESS_KEY']
    BUCKET_NAME = ''
    BASE_PATH = ''

    def __init__(self):
        self.s3 = boto3.resource('s3',
                                 aws_access_key_id=ACCESS_KEY,
                                 aws_secret_access_key=SECRET_KEY)

    def upload_object(data):
        s3.Bucket(bucket_name).put_object(
            Key='{0}/{1}'.format(BASE_PATH, current_minute), Body=data)

    def list_objects(self):

    def modify_object(self):

    def delete_object(self):



CLICK_CONTEXT_SETTINGS = dict(
    help_option_names=['-h', '--help'],
    token_normalize_func=lambda param: param.lower(),
    ignore_unknown_options=True)


@click.group(context_settings=CLICK_CONTEXT_SETTINGS, cls=DYMGroup)
@click.pass_context
def s3s(ctx):
    """S3S Command Line Interface

    """
    ctx.obj = {}
    ctx.obj['client'] = s3Client(object)