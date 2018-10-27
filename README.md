# Backup

Disk- and time-efficient backup solution

## What?

This module is a solution for backing up UNIX computer systems.  It
might work for Windows also, but it probably needs some tweaks to make
that work.

It uses hash-based deduplication to save space on the backup media.
Every complete backup can stand on its own with the deduplicated file
repository, so there is no need to differentiate between a full and an
incremental backup.

## Why?

I have several computers to back up.  Some of them have files that
don't change often.  Some of them have systems in place like Dropbox,
Resilio Sync or Syncthing that result in identical files being in
place on multiple machines.  This allows me to back up All The Things
without having to think about that.

## How?

You can use it two ways:  As a standalone program or as a module.

There are two prerequisites: CAS and Bumddb.  Both of these are Python
modules that can be found on Github where this one was found.  Put
them where Python can find them.

### As a standalone

You can do this:

    backup.py --help

...to get a command synopsis.

For starters, you will need your backup media mounted.  Create a
directory on it.  Let's assume that it is located at /mnt/backup.  You
can do these things:

#### Backup

    backup.py backup /mnt/backup /etc /home /opt /root /usr/local

You are issuing the command 'backup', using /mnt/backup as the backup
storage space, and making a backup of /etc, /home, /opt, /root and
/user/local.

#### List

    backup.py list /mnt/backup

You are issuing the command 'list'.  It will list off all of the
backups made from this host.

#### Search

    backup.py search /mnt/backup somefile

You are issuing the command 'search'.  It will search for all files in
any backup made from this host that has 'somefile' as a substring, and
give you the timestamps of the different versions, if there is more
than one result.

#### Restore

    backup.py restore /mnt/backup -i 1

You are issuing the command 'restore' to restore everything that was
backed up in backup #1 from this host.  You can use 'list' (see above)
to figure out what the backup number should be.

#### Options

-v --verbose

Offer more detail on the screen while running.  Recommended for the
first few times until you get used to the program.

-m --mdbtath

Put the database someplace other than the default.  By default, the
database will be in a file named after the host, with the extension
.db, located under the backup dir.  For instance, if the backup dir is
/mnt/backup and the host is named Thor, then the database will be
/mnt/backup/Thor.db.

If you specify a relative path, the path will be relative to the
backup dir.  If you specify an absolute path, it will be used as an
absolute path.

-r --repository

Put the file repository somethlace other than the default.  By
default, the file repository is in a folder named repository under the
backup dir.  For instance, if the backup dir is /mnt/backup, then the
file repository is /mnt/backup/repository.

If you specify a relative path, the path will be relative to the
backup dir.  If you specify an absolute path, it will be used as an
absolute path.

-n --node

Use this as the host name rather than the actual host name.  This will
allow you to backup files from a disk you've mounted from another
system, or to restore, search or list files from another system.

-d --dest

Use this to set the destination where files should be restored to
during a restore operation.  Other operations will ignore this
setting.

-s --sourcebase

Treat this directory as if it were root.  This will allow you to
backup files from a disk you've mounted from another system as though
they were backed up from that system.

-i --runid

Use this to identify what run should be used to restore files.  It is
mandatory for restore operations, and ignored for all others.

### As a module

Start by importing.

    from backup import Backup

#### Instantiating the backup

    backup = Backup(backupBasePath, dbPath = None, repoPath = None,
        host = None, runId = None, destination = None, sourceBase =
        None, verbose = False)

The named parameters correspond to the command line options (see
above) as follows:

       -v    verbose = True
       -m    dbPath = <path>
       -r    repoPath = <path>
       -n    host = <hostname>
       -i    runId = <backup number>
       -s    sourceBase = <path>
       -d    destination = <path>

Additionally, the required parameter backupBasePath is equivalent to
the "remote" parameter in the command line usage.

#### Backup

    backup.backup(subjectlist)

subjectlist is expected to be an array containing the paths to be
backed up.  You do not need to fully enumerate everything to back up:
each subject in the list will be walked recursively.

#### List

    backup.list(notBefore = None, notAfter = None)

This will list backups to the screen.  The values of notBefore and
notAfter can be used to narrow this down to a slice of time.  They
should be an integer/float of the format provided by time.time().

For machine-readable formatting, you can do this instead:

    backup.runTable.listBackups(backup.host, notBefore, notAfter)

... which will call on the instance of Bumddb.RunTable rather than
using your Backup instance directly.  It will yield each result as a
dict of parameters.

#### Search

    backup.search(subjectlist)

subjectlist is expected to be an array.  The search method will loop
over the elements in the array, and produce a printed output listing
every file, symlink or directory that has each subject as a substring.
Note that this search is NOT CASE SENSITIVE.

For machine-readable formatting, you can do this instead:

    backup.filepathTable.search(subjectlist)

... which will call on the instance of Bumddb.FilepathTable rather
than using your Backup instance directly.  It will yield each result
as a dict of parameters.

#### Restore

    backup.restore(subjectlist)

subjectlist is expected to be an array.

If subjectlist is empty, then everything will be restored from backup
of the host and runId specified when you instantiated the Backup
object.

If subjectlist is not empty, restore will iterate over the subjects
and restore the objects whose paths begin with the subject as a
substring.  Note that this search is NOT CASE SENSITIVE.

