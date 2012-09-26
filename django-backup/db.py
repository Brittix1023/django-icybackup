import os
from django.core.management.base import CommandError
from tempfile import mkstemp

def backup(database, outfile):
    engine = database['ENGINE']
    if 'mysql' in engine:
        __mysql_backup(database, outfile)
    elif engine in ('postgresql_psycopg2', 'postgresql') or 'postgresql' in engine:
        __postgresql_backup(database, outfile)
    elif 'sqlite3' in engine:
        __sqlite_backup(database, outfile)
    else:
        raise CommandError('Backup in %s engine not implemented' % engine)

def __sqlite_backup(database, outfile):
    os.system('cp %s %s' % (database['NAME'], outfile))

def __mysql_backup(database, outfile):
    args = []
    if 'USER' in database:
        args += ["--user=%s" % database['USER']]
    if 'PASSWORD' in database:
        args += ["--password=%s" % database['PASSWORD']]
    if 'HOST' in database:
        args += ["--host=%s" % database['HOST']]
    if 'PORT' in database:
        args += ["--port=%s" % database['PORT']]
    args += [database['NAME']]

    os.system('mysqldump %s > %s' % (' '.join(args), outfile))

def __postgresql_backup(database, outfile):
    args = []
    if 'USER' in database:
        args += ["--username=%s" % database['USER']]
    if 'HOST' in database:
        args += ["--host=%s" % database['HOST']]
    if 'PORT' in database:
        args += ["--port=%s" % database['PORT']]
    if 'NAME' in database:
        args += [database['NAME']]
    
    if 'PASSWORD' in database:
        # create a pgpass file that always returns the same password, as a secure temp file
        password_fd, password_path = mkstemp()
        password_file = os.fdopen(password_fd, 'w')
        password_file.write('*:*:*:*:{}'.format(database['PASSWORD']))
        password_file.close()
        os.environ['PGPASSFILE'] = password_path
    
    os.system('pg_dump %s -w > %s' % (' '.join(args), outfile))
    
    # clean up
    if password_path:
        os.remove(password_path)
