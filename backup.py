#!/usr/bin/python3

import cas
import bumddb
import sqlite3
import os
import platform
import time
import argparse

class Backup:
    def __init__(self, backupBasePath, dbPath = None, repoPath = None,
                 host = None, runId = None, destination = None,
                 sourceBase = None, verbose = False):

        #backupBasePath - databases and repo directory would be here by default.
        
        #dbPath - if absolute, it's a path to the database.  .db will
        #be added if it's not there.  If relative, it will be relative
        #to backupBasePath.  If None, it will default to the hostname
        #with .db tacked onto it.

        #repoPath - if absolute, it's a path to the repository
        #directory.  If relative, it will identify the repository dir
        #relative to backupBasePath.  If None, it will be set to
        #backupBasePath/repository.

        #host - Override for the server's host name.

        #runId - Override for the run_id.  Will be ignored by backup().

        #destination - Used by restore() ignored by everything else.
        #Where do you want the restored files to go?

        #sourceBase - In backup operations, this will be stripped off
        #of the start of the absolute path and replaced with '/'.  For
        #instance, if this is set to /home/smith then
        #/home/smith/.bashrc will be backed up as /.bashrc.  If set to
        #None, real absolute paths will be used.

        self.verbose = verbose
        print ("backupBasePath is ", backupBasePath)
        self.backupBasePath = os.path.abspath(backupBasePath)
        
        if (host is None):
            self.host = platform.node()
        else:
            self.host = host

        if (dbPath is None):
            self.dbPath = os.path.join(backupBasePath, (self.host + ".db"))
        elif (os.path.isabs(dbPath)):
            self.dbPath = dbPath
        else:
            self.dbPath = os.path.join(backupBasePath, dbPath)
            
        if not (self.dbPath.endswith(".db")):
            self.dbPath += ".db"

        if (repoPath is None):
            self.repoPath = os.path.join(backupBasePath, "repository")
        elif (os.path.isabs(repoPath)):
            self.repoPath = repoPath
        else:
            self.repoPath = os.path.join(backupBasePath, repoPath)

        self.dbh = sqlite3.connect(self.dbPath)
        
        self.runId = runId
        
        self.destination = destination

        self.sourceBase = sourceBase

        self.cas = cas.CAS(self.repoPath)
        self.runTable = bumddb.RunTable(self.dbh, create = True)
        self.statusTable = bumddb.StatusTable(self.dbh, create = True)
        self.hostTable = bumddb.HostTable(self.dbh, create = True)
        self.fileshaTable = bumddb.FileshaTable(self.dbh, create = True)
        self.filepathTable = bumddb.FilepathTable(self.dbh, create = True)
        self.directoryTable = bumddb.DirectoryTable(self.dbh, create = True)
        self.linkTable = bumddb.LinkTable(self.dbh, create = True)
        self.fileTable = bumddb.FileTable(self.dbh, create = True)

    def getUsablePaths(self, path):

        realFilePath = os.path.abspath(path)
        if (self.sourceBase is None):
            filePath = realFilePath
        else:
            filepath = "/" + os.path.relpath(path, self.sourceBase)

        return realFilePath, filePath
        
    def backup(self, subjectlist):
        self.runId = self.runTable.getId(self.host, time.time())
        self.dbh.commit()

        print ("Run ID is", self.runId)
        
        self.runTable.updateStatus(self.runId, "Running")
        
        for subject in subjectlist:
            for directory in os.walk(subject):
                realFilePath, filePath = self.getUsablePaths(directory[0])
                stats = os.lstat(realFilePath)
                self.directoryTable.getId(self.runId, filePath, stats.st_uid, stats.st_gid, stats.st_mode, stats.st_mtime)
                print ("DIR  ", realFilePath)
                
                for subfile in directory[2]:
                    realFilePath, filePath = self.getUsablePaths(os.path.join(directory[0], subfile))
                    if (os.path.islink(realFilePath)):
                        destPath = os.readlink(realFilePath)
                        self.linkTable.getId(self.runId, filePath, destPath)
                        print ("LINK ", realFilePath)
                        
                    elif (os.path.isfile(realFilePath)):
                        stats = os.lstat(realFilePath)
                        existing = self.fileTable.getExistingRecord(self.host, filePath, stats.st_size, stats.st_mtime)
                        if (existing is None):
                            if (self.verbose): print ("HASH ", realFilePath)
                            filesha = self.cas.hashfile(realFilePath)
                        else:
                            if (self.verbose): print ("REUSE", realFilePath)
                            filesha = existing
                        
                        self.fileTable.getId(self.runId, filePath, stats.st_uid, stats.st_gid, stats.st_mode, stats.st_size, stats.st_mtime, filesha)

                        if (self.cas.isvalidkey(filesha)):
                            pass
                        else:
                            print ("SEND ", realFilePath)
                            self.cas.putfile(realFilePath, filesha)

                    else:
                        pass

                self.dbh.commit()

        self.runTable.updateStatus(self.runId, "Complete")
        self.runTable.updateEndtime(self.runId, time.time())
        self.dbh.commit()
        print ("Backup completed.")

    def list(self, notBefore = None, notAfter = None):
        for result in self.runTable.listBackups(self.host, notBefore, notAfter):
            print ("%6d %12s %19s %19s %10s" % (
                result['runId'],
                result['host'],
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result['starttime'])),
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result['endtime'])),
                result['status']
            ))

    def search (self, subjectlist):
        for result in self.filepathTable.search(subjectlist):
            print ("%4s %12s %19s %s" % (
                result['type'],
                result['host'],
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result['filetime'])),
                result['filepath']
            ))

    def restore(self, subjectlist):
        for result in self.directoryTable.restoreList(self.runId, subjectlist):
            newdir = os.path.abspath(os.path.join(self.destination, os.path.relpath(result['filepath'], '/')))
            if (self.verbose):
                print ("DIR  ", newdir)

            if (os.path.exists(newdir)):
                if (not os.path.isdir(newdir)):
                    raise Exception ("Unable to create directory %s: something else is already there." % newdir)
            else:
                os.makedirs(newdir)
            os.chown (newdir, result['fileowner'], result['filegroup'])
            os.chmod (newdir, result['filemode'])
            os.utime(newdir, (result['filetime'], result['filetime']))

        for result in self.linkTable.restoreList (self.runId, subjectlist):
            newlink = os.path.abspath(os.path.join(self.destination, os.path.relpath(result['filepath'], '/')))
            if (self.verbose):
                print ("LINK ", newlink)

            if (os.path.islink(newlink)):
                os.remove(newlink)
            if (os.path.exists(newlink) and not os.path.islink(newlink)):
                raise Exception ("Unable to create link %s: something else is already there." % newlink)
            os.symlink(result['destpath'], result['newlink'])

        for result in self.fileTable.restoreList (self.runId, subjectlist):
            newfile = os.path.abspath(os.path.join(self.restdest, os.path.relpath(result['filepath'], '/')))
            if (self.verbose):
                print ("FILE ", newfile)

            self.cas.getfile(result['filesha'], newfile)
            if (self.verbose):
                print ("FILE ", newfile)
            os.chown(newfile, result['fileowner'], result['filegroup'])
            os.chmod(newfile, result['filemode'])
            os.utime(newfile, (result['filetime'], result['filetime']))

            
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true")
    parser.add_argument("-m", "--mdbpath", help="Path or filename to database", type=str)
    parser.add_argument("-r", "--repository", help="Path to the repository", type=str)
    parser.add_argument("-n", "--node", help="Hostname to use in the backup", type=str)
    parser.add_argument("-i", "--runid", help="Run ID number", type=int)
    parser.add_argument("-d", "--dest", help="Destination for restore", type=str)
    parser.add_argument("-s", "--sourcebase", help="Base path to use in the backup", type=str)
    parser.add_argument("command", help="What action to take: backup, restore, list, search", type=str, choices=['backup','restore','list','search'])
    parser.add_argument("remote", help="Base path to backup storage", type=str)
    parser.add_argument("subject", help="Items to be backed up or restored", type=str, nargs="*")
    args = parser.parse_args()

    if (args.verbose):
        print ("verbose", args.verbose)
        print ("mdbpath", args.mdbpath)
        print ("repository", args.repository)
        print ("node", args.node)
        print ("runid", args.runid)
        print ("dest", args.dest)
        print ("sourcebase", args.sourcebase)
        print ("command", args.command)
        print ("remote", args.remote)
        print ("subject", args.subject)
    
    backup = Backup(backupBasePath = args.remote,
                    dbPath = args.mdbpath,
                    repoPath = args.repository,
                    host = args.node,
                    destination = args.dest,
                    sourceBase = args.sourcebase,
                    verbose = args.verbose)
    if (args.command == "backup"):
        backup.backup(args.subject)
    elif (args.command == "list"):
        if (len(args.subject) < 1):
            startTime = None
        if (len(args.subject) < 2):
            endTime = None
        backup.list(startTime, endTime)
    elif (args.command == 'search'):
        backup.search(args.subject)
    else:
        raise NotImplementedError(args.command)

if (__name__ == "__main__"):
    main()

