import os
import json
import datetime

import click
import boto3

from click_didyoumean import DYMGroup


CONFIG_PATH = '{0}/s3s-config.json'.format(os.getenv("HOME"))
with open(CONFIG_PATH) as config_file:
    cfg = json.load(config_file)["s3s"]


BUCKET_NAME = os.environ.get('S3S_BUCKET')


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()

def _format_json(dictionary):
    return json.dumps(dictionary, indent=4, sort_keys=True)


def _get_date(addDays=0, dateFormat="%Y, %m, %d"):

    current_date = datetime.datetime.now()
    if (addDays!=0):
        experation_date = current_date + datetime.timedelta(days=addDays)
    else:
        experation_date = current_date

    return experation_date.strftime(dateFormat)


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


class aws_client():


    def __init__(self):
        if os.environ.get('S3S_ACCESS_KEY_ID'):
            ACCESS_KEY = os.environ.get('S3S_ACCESS_KEY_ID')
        self.ACCESS_KEY = ACCESS_KEY

        if os.environ.get('S3S_SECRET_ACCESS_KEY'):
            SECRET_KEY = os.environ.get('S3S_SECRET_ACCESS_KEY')
        self.SECRET_KEY = SECRET_KEY


    def aws_api(self, resource=True, aws_service='s3'):
        if resource:
            return boto3.resource(aws_service,
                                   aws_access_key_id=self.ACCESS_KEY,
                                   aws_secret_access_key=self.SECRET_KEY)
        else:
            return boto3.client(aws_service,
                                      aws_access_key_id=self.ACCESS_KEY,
                                      aws_secret_access_key=self.SECRET_KEY)


    def handle_buckets(self):
        buckets = self.aws_api(resource=False).list_buckets()['Buckets']
        for bucket in buckets:
            if bucket['Name'] == BUCKET_NAME:
                break
            else:
                self.aws_api(resource=False).create_bucket(
                    Bucket=BUCKET_NAME,
                    CreateBucketConfiguration={
                        'LocationConstraint': 'eu-west-1'})


    def upload_to_aws(self, file_to_upload):
        self.handle_buckets()
        bucket = self.aws_api().Bucket(BUCKET_NAME)
        if os.path.isfile(file_to_upload):
            with open(file_to_upload) as content:
                bucket.put_object(Key=file_to_upload,Body=content)
            print self.aws_api(resource=False).generate_presigned_url('get_object', Params = {'Bucket': BUCKET_NAME, 'Key': file_to_upload}, ExpiresIn = 100)
        elif os.path.isdir(file_to_upload):
            folder_name = os.path.basename(file_to_upload)
            folder_content = os.listdir(file_to_upload)
            for file_to_upload in folder_content:
                if os.path.isfile(file_to_upload):
                    with open(file_to_upload) as content:
                        bucket.put_object(Key='{}/{}'.format(folder_name,file_to_upload),Body=content)
                    print '{}/{}\n{}'.format(folder_name,file_to_upload,self.aws_api(resource=False).generate_presigned_url('get_object', Params = {'Bucket': BUCKET_NAME, 'Key': file_to_upload}, ExpiresIn = 100))


    def list_s3_content(self, dimension):
        buckets = self.aws_api(resource=False).list_buckets()['Buckets']
        if dimension.lower() == 'buckets':
            for bucket in buckets:
                print bucket['Name']
        elif dimension.lower() == 'folders':
            for bucket in buckets:
                result = self.aws_api(resource=False).list_objects(Bucket=bucket['Name'], Delimiter='/')
                print 'Bucket: {}'.format(bucket['Name'])
                if result.get('CommonPrefixes'):
                    for o in result.get('CommonPrefixes'):
                        print 'folders: ', o.get('Prefix')
                else:
                    print 'bucket is empty'
                print '-'*10
        elif dimension.lower() == 'files':
            buckets_dict = {}
            files_list = []
            for bucket in buckets:
                bucket_name = bucket['Name']
                bucket_dict = {}
                buckets_dict[bucket_name] = bucket_dict
                my_bucket = self.aws_api().Bucket(bucket['Name'])
                for object in my_bucket.objects.all():
                    files_list.append(object.key)
                bucket_dict['Files'] = files_list
                files_list = []
            print _format_json(buckets_dict)


    def purge_s3_bucket(self, bucket_name):
        all_objects = self.aws_api(resource=False).list_objects(Bucket = bucket_name)
        for file in all_objects['Contents']:
            self.aws_api(resource=False).delete_object(Bucket=bucket_name, Key=file['Key'])


CLICK_CONTEXT_SETTINGS = dict(
    help_option_names=['-h', '--help'],
    token_normalize_func=lambda param: param.lower())

@click.group(context_settings=CLICK_CONTEXT_SETTINGS, cls=DYMGroup)
@click.pass_context
def _s3s(ctx):
    """Client to upload files to S3 easily
    """
    ctx.obj = {}
    ctx.obj['client'] = aws_client()


@_s3s.command('set')
@click.option('--S3S_BUCKET', prompt=True)
def set_s3s(s3s_bucket):
    """Set your active Bucket"""
    os.environ["S3S_BUCKET"] = s3s_bucket


@_s3s.command('list')
@click.argument('dimension')
def list(dimension):
    """List S3 content
    """
    client = aws_client()
    client.list_s3_content(dimension)\


@_s3s.command('upload')
@click.argument('filename')
def upload(filename):
    """Upload files to S3
    """
    client = aws_client()
    client.upload_to_aws(filename)


@_s3s.command('purge')
@click.option('--yes', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Are you sure you want to drop the db?')
@click.argument('bucket')
def upload(bucket):
    """Delete entire content of S3 Bucket
    """
    client = aws_client()
    client.purge_s3_bucket(bucket)

