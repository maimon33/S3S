import os
import sys
import json
import time

import click
import boto3
import zipfile


CONFIG_PATH = '{0}/s3s-config.json'.format(os.getenv("HOME"))
with open(CONFIG_PATH) as config_file:
    cfg = json.load(config_file)["s3s"]

SIGNATURE = """This Email was sent by S3S.
A tool to easily upload and share content via AWS S3
To learn more visit Github repo https://github.com/maimon33/S3S"""


def _abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


def _format_json(dictionary):
    return json.dumps(dictionary, indent=4, sort_keys=True)


def _name_your_bucket():
    import random
    import string
    if os.environ.get('S3S_BUCKET'):
        BUCKET_NAME = os.environ['S3S_BUCKET']
        return BUCKET_NAME
    else:
        BUCKET_NAME = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(16))
        return BUCKET_NAME


def _send_mail(destination, expire_in, subject, msg):
    if cfg["enable_mailer"]:
        import smtplib

        msg = 'Links will expire in {} Days\n\n{}'.format(expire_in, msg)
        msg_with_signature = '{}\n\n{}'.format(msg, SIGNATURE)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(cfg["mailer_username"], cfg["mailer_password"])
        server.sendmail(cfg["mailer_username"], destination,
                        'Subject: {}\n\n{}'.format(subject, msg_with_signature))
        server.quit()
    else:
        pass


def _isvalidemail(email):
    import re

    match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email)

    if match == None:
        print 'Bad Syntax - Invalid Email Address'
        sys.exit()


class aws_client():


    def __init__(self):
        ACCESS_KEY = os.environ.get('S3S_ACCESS_KEY_ID')
        self.ACCESS_KEY = ACCESS_KEY

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


    def handle_buckets(self, BUCKET_NAME):
        buckets = self.aws_api(resource=False).list_buckets()['Buckets']
        for bucket in buckets:
            if BUCKET_NAME in bucket['Name']:
                break
            else:
                self.aws_api(resource=False).create_bucket(
                    Bucket=BUCKET_NAME,
                    CreateBucketConfiguration={
                        'LocationConstraint': 'eu-west-1'})
                break


    def zip_content(self, file_to_upload):
        zip_filename = zipfile.ZipFile(file_to_upload, 'w')
        zip_filename.write(file_to_upload, compress_type=zipfile.ZIP_DEFLATED)
        zip_filename.close()
        return zip_filename


    def upload_to_aws(self, file_to_upload, expire_in, make_public):
        BUCKET_NAME = _name_your_bucket()
        EXPIRE_CONVERTED_TO_SECONDS = expire_in * 86400
        files_links = []
        upload_summery = []
        self.handle_buckets(BUCKET_NAME)
        bucket = self.aws_api().Bucket(BUCKET_NAME)
        if os.path.isfile(file_to_upload):
            print 'Starting File Upload'
            with open(file_to_upload) as content:
                start = time.time()
                try:
                    file_to_upload.encode('ascii')
                except UnicodeEncodeError:
                    print 'Skipping {} - Bad filename'.format(file_to_upload.encode('UTF-8'))
                    sys.exit()
                bucket.put_object(Key=file_to_upload,Body=content)
                print '\nFile {} uploaded in {}'.format(file_to_upload, time.time() - start)
                if make_public:
                    return '{} - {}'.format(
                        file_to_upload, self.aws_api(resource=False).generate_presigned_url(
                        'get_object',
                        Params = {'Bucket': BUCKET_NAME, 'Key': file_to_upload},
                        ExpiresIn = EXPIRE_CONVERTED_TO_SECONDS))
        elif os.path.isdir(file_to_upload):
            os.chdir(os.path.realpath(file_to_upload))
            folder_name = os.path.basename(os.path.realpath(file_to_upload))
            print os.listdir(os.path.realpath(file_to_upload))
            folder_content = os.listdir(file_to_upload)
            print 'Starting Folder Upload\n',
            for file_to_upload in folder_content:
                start = time.time()
                if os.path.isfile(file_to_upload):
                    with open(file_to_upload) as content:
                        try:
                            file_to_upload.encode('ascii')
                        except UnicodeEncodeError:
                            upload_summery.append('Skipping {} - Bad filename'.format(
                                file_to_upload.encode('UTF-8')))
                            continue
                        bucket.put_object(
                            Key='{}/{}'.format(folder_name, file_to_upload),
                            Body=content)
                    upload_summery.append('File {} uploaded in {}'.format(
                        file_to_upload, time.time() - start))
                    print '\b.',
                    sys.stdout.flush()
                    if make_public:
                        files_links.append('{} - {}'.format(
                            file_to_upload, self.aws_api(resource=False).generate_presigned_url(
                            'get_object',
                            Params = {'Bucket': BUCKET_NAME,
                                      'Key': '{}/{}'.format(folder_name,
                                                            file_to_upload)},
                            ExpiresIn = EXPIRE_CONVERTED_TO_SECONDS)))
                elif os.path.isdir(file_to_upload):
                    upload_summery.append('Skipping folder {}'.format(file_to_upload))
            print '\nDone!'
            print _format_json(upload_summery)
            return _format_json(files_links)


    def fetch_bucket_objects(self, bucket_name):
        object_list = []
        my_bucket = self.aws_api().Bucket(bucket_name)
        for object in my_bucket.objects.all():
            object_list.append(object.key)
        return object_list


    def list_s3_content(self, dimension):
        buckets = self.aws_api(resource=False).list_buckets()['Buckets']
        if dimension.lower() == 'buckets':
            for bucket in buckets:
                print bucket['Name']
        elif dimension.lower() == 'folders':
            for bucket in buckets:
                result = self.aws_api(resource=False).list_objects(
                    Bucket=bucket['Name'],
                    Delimiter='/')
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
        else:
            print "No Such Object Type"


    def regenerate_links(self, bucket, object_name, expire_in):
        EXPIRE_CONVERTED_TO_SECONDS = expire_in * 86400
        objects = self.fetch_bucket_objects(bucket)
        files_links = []
        for file in objects:
            if file == object_name:
                print '{} -  {}'.format(file, self.aws_api(resource=False).generate_presigned_url(
                    'get_object',
                    Params = {'Bucket': bucket, 'Key': file},
                    ExpiresIn = EXPIRE_CONVERTED_TO_SECONDS))
            elif file.startswith('{}/'.format(object_name)):
                files_links.append('{} - {}'.format(file, self.aws_api(resource=False).generate_presigned_url(
                    'get_object',
                    Params = {'Bucket': bucket, 'Key': file},
                    ExpiresIn = EXPIRE_CONVERTED_TO_SECONDS)))
            else:
                return 'No Object Found by that name'
        return files_links


    def purge_s3_bucket(self, bucket_name):
        all_objects = self.aws_api(resource=False).list_objects(Bucket = bucket_name)
        try:
            all_objects['Contents']
        except KeyError:
            print 'Bucket {} is already empty'.format(bucket_name)
            sys.exit()
        for file in all_objects['Contents']:
            self.aws_api(resource=False).delete_object(Bucket=bucket_name,
                                                       Key=file['Key'])


class AliasedGroup(click.Group):
    def __init__(self, *args, **kwargs):
        self.max_suggestions = kwargs.pop("max_suggestions", 3)
        self.cutoff = kwargs.pop("cutoff", 0.5)
        super(AliasedGroup, self).__init__(*args, **kwargs)

    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = \
            [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail('Too many matches: {0}'.format(', '.join(sorted(matches))))


CLICK_CONTEXT_SETTINGS = dict(
    help_option_names=['-h', '--help'],
    token_normalize_func=lambda param: param.lower(),
    ignore_unknown_options=True)

@click.group(context_settings=CLICK_CONTEXT_SETTINGS, cls=AliasedGroup)
@click.pass_context
def _s3s(ctx):
    """Client to upload files to S3 easily
    """
    if os.environ.get('S3S_ACCESS_KEY_ID') and os.environ.get(
            'S3S_SECRET_ACCESS_KEY'):
        ctx.obj = {}
        ctx.obj['client'] = aws_client()
    else:
        print 'AWS credentials missing'
        # Kill process, AWS credentials are missing. no point moving forward!
        sys.exit()


@_s3s.command('list')
@click.argument('dimension')
def list(dimension):
    """List S3 content
    
    DIMENSIONS is the scope of objects to list (buckets, folders and files)
    """
    client = aws_client()
    client.list_s3_content(dimension)


@_s3s.command('upload')
@click.option('-p',
              '--make-public',
              is_flag=True,
              help='Do you want to have a public link to the files?')
@click.option('-e',
              '--expire-in',
              default=30,
              help='The Number of days the link is active')
@click.option('-s',
              '--send-to',
              help='email address to send to')
@click.option('-z',
              '--zip',
              is_flag=True,
              help='Archive Folder before upload')
@click.argument('filename')
def upload(filename, expire_in, send_to, make_public, zip):
    """Upload files to S3
    
    FILENAME is name of Folder or File you wish to upload 
    """
    client = aws_client()
    if expire_in < 1:
        print "The value of expire-in must be greater then 0"
    else:
        if zip:
            jungle_zip = zipfile.ZipFile('{}.zip'.format(filename), 'w', zipfile.ZIP_DEFLATED)
            for root, dirs, files in os.walk(os.path.realpath(filename), topdown=False):
                for name in files:
                    zip_object = os.path.join(root, name)
                    jungle_zip.write(zip_object)
            jungle_zip.close()
            filename = '{}.zip'.format(filename)
        else:
            pass

        if send_to:
            if _isvalidemail(send_to) == 'Bad Syntax':
                print "Bad Email address"
            else:
                _send_mail(send_to, expire_in,
                           "Files were Shared with you!",
                           _format_json(client.upload_to_aws(filename,
                                                             expire_in,
                                                             make_public=True)))
        elif make_public:
            print "Test"
            print _format_json(client.upload_to_aws(filename,
                                                    expire_in,
                                                    make_public=True))

        else:
            client.upload_to_aws(filename,
                                 expire_in,
                                 make_public=False)


@_s3s.command('regen-links')
@click.option('-b',
              '--bucket-name',
              required=True,
              envvar='S3S_BUCKET',
              help='Name the bucket your working on')
@click.option('-e',
              '--expire-in',
              default=30,
              help='The Number of days the link is active')
@click.option('-s',
              '--send-to',
              help='email address to send to')
@click.argument('object-name')
def regen_links(bucket_name, object_name, expire_in, send_to):
    """Regenerate public links
    
    OBJECT-NAME is the regex string to match with the object in S3 
    """
    client = aws_client()
    if expire_in < 1:
        print "The value of expire-in must be greater then 0"
    else:
        if send_to:
            if _isvalidemail(send_to) == 'Bad Syntax':
                print "Bad Email address"
            else:
                _send_mail(send_to, expire_in,
                           "Files were Shared with you!",
                           _format_json(client.regenerate_links(bucket_name,
                                                                object_name,
                                                                expire_in)))
        else:
            print _format_json(client.regenerate_links(bucket_name,
                                                       object_name,
                                                       expire_in))


@_s3s.command('purge')
@click.option('--yes', is_flag=True, callback=_abort_if_false,
              expose_value=False,
              prompt='Are you sure you want empty the bucket?')
@click.argument('bucket')
def purge(bucket):
    """Delete all objects in an S3 Bucket
    """
    client = aws_client()
    client.purge_s3_bucket(bucket)
