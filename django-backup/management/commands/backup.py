import os, popen2, time
from datetime import datetime
from optparse import make_option
from tempfile import mkdtemp

from ... import db

from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.sites.models import Site

# Based on: http://code.google.com/p/django-backup/
# Based on: http://www.djangosnippets.org/snippets/823/
# Based on: http://www.yashh.com/blog/2008/sep/05/django-database-backup-view/
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--email', '-m', default=None, dest='email',
            help='Sends email with attached dump file'),
        make_option('--compress', '-c', action='store_true', default=False, dest='compress',
            help='Compress SQL dump file using GZ'),
        make_option('--directory', '-d', action='append', default=[], dest='directories',
            help='Include Directories'),
        make_option('--zipencrypt', '-z', action='store_true', default=False,
            dest='zipencrypt', help='Compress and encrypt SQL dump file using zip'),
        make_option('--backup_docs', '-b', action='store_true', default=False,
            dest='backup_docs', help='Backup your docs directory alongside the DB dump.'),

    )
    help = "Backup database. Only Mysql, Postgresql and Sqlite engines are implemented"

    def _time_suffix(self):
        return time.strftime('%Y%m%d-%H%M%S')

    def handle(self, *args, **options):
        self.email = options.get('email')
        self.compress = options.get('compress')
        self.directories = options.get('directories')
        self.zipencrypt = options.get('zipencrypt')
        self.backup_docs = options.get('backup_docs')
        if 'site' in settings.INSTALLED_APPS:
            self.current_site = Site.objects.get_current()
        else:
            self.current_site = ''
        self.encrypt_password = "ENTER PASSWORD HERE"
        
        if hasattr(settings, 'DATABASES'):
            database_list = settings.DATABASES
        else:
            # database details are in the old format, so convert to the new one
            database_list = {
                'default': {
                    'ENGINE': settings.DATABASE_ENGINE,
                    'NAME': settings.DATABASE_NAME,
                    'USER': settings.DATABASE_USER,
                    'PASSWORD': settings.DATABASE_PASSWORD,
                    'HOST': settings.DATABASE_HOST,
                    'PORT': settings.DATABASE_PORT,
                }
            }
            
        self.media_directory = settings.MEDIA_ROOT
            
        backup_dir = 'backups'
        if self.backup_docs:
            backup_dir = "backups/%s" % self._time_suffix()
            
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        outfile = os.path.join(backup_dir, 'backup_%s.sql' % self._time_suffix())
        
        # Create a temporary directory to perform our backup in
        backup_root = mkdtemp()
        database_root = os.path.join(backup_root, 'databases')
        os.mkdir(database_root)
        
        print backup_root

        #Backup documents?
        if self.backup_docs:
            print "Backing up documents directory to %s from %s" % (backup_dir,self.media_directory)
            dir_outfile = os.path.join(backup_dir, 'media_backup.tar.gz')
            self.compress_dir(self.media_directory, dir_outfile)

        # Back up databases
        for name, database in database_list.iteritems():
            db.backup(database, os.path.join(database_root, name))

        # Compressing backup
        if self.compress:
            compressed_outfile = outfile + '.gz'
            print 'Compressing backup file %s to %s' % (outfile, compressed_outfile)
            self.do_compress(outfile, compressed_outfile)
            outfile = compressed_outfile
            
        #Zip & Encrypting backup
        if self.zipencrypt:
            zip_encrypted_outfile = outfile + ".zip"
            print 'Ziping and Encrypting backup file %s to %s' % (outfile, zip_encrypted_outfile)
            self.do_encrypt(outfile, zip_encrypted_outfile)
            outfile = zip_encrypted_outfile

        # Backuping directoris
        dir_outfiles = []
        for directory in self.directories:
            dir_outfile = os.path.join(backup_dir, '%s_%s.tar.gz' % (os.path.basename(directory), self._time_suffix()))
            dir_outfiles.append(dir_outfile)
            print("Compressing '%s' to '%s'" % (directory, dir_outfile))
            self.compress_dir(directory, dir_outfile)

        # Sending mail with backups
        if self.email:
            print "Sending e-mail with backups to '%s'" % self.email
            self.sendmail(settings.SERVER_EMAIL, [self.email], dir_outfiles + [outfile])

    def compress_dir(self, directory, outfile):
        os.system('tar -czf %s %s' % (outfile, directory))

    def sendmail(self, address_from, addresses_to, attachements):
        subject = "Your DB-backup for %s %s" % (datetime.now().strftime("%d %b %Y"), self.current_site)
        body = "Timestamp of the backup is " + datetime.now().strftime("%d %b %Y")

        email = EmailMessage(subject, body, address_from, addresses_to)
        email.content_subtype = 'html'
        for attachement in attachements:
            email.attach_file(attachement)
        email.send()

    def do_compress(self, infile, outfile):
        os.system('gzip --stdout %s > %s' % (infile, outfile))
        os.system('rm %s' % infile)

    def do_encrypt(self, infile, outfile):
        os.system('zip -P %s %s %s' % (self.encrypt_password, outfile, infile))
        os.system('rm %s' % infile)        
        
        #os.system('gpg --yes --passphrase %s -c %s' % (self.encrypt_password, infile))        
        #os.system('rm %s' % infile)

