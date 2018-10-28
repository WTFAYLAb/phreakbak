#!/usr/bin/python3

import bumddb
import sqlite3
import argparse

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument ("hostname", help="Host name", type = str)
    args = parser.parse_args()

    sourceDB = sqlite3.connect("databases/legacy/%s.db" % (args.hostname))
    destDB   = sqlite3.connect("databases/v1/%s.db" % (args.hostname))

    statusTable = bumddb.StatusTable(destDB, create = True)
    hostTable = bumddb.HostTable(destDB, create = True)
    fileshaTable = bumddb.FileshaTable(destDB, create = True)
    filepathTable = bumddb.FilepathTable(destDB, create = True)
    runTable = bumddb.RunTable(destDB, create = True)
    dirTable = bumddb.DirectoryTable(destDB, create = True)
    linkTable = bumddb.LinkTable(destDB, create = True)
    fileTable = bumddb.FileTable(destDB, create = True)

    counterCursor = sourceDB.cursor()

    counterCursor.execute("SELECT COUNT(0) FROM run", [])
    runCount = counterCursor.fetchone()[0]
    
    runNumber = 0
    runCursor = sourceDB.cursor()
    runCursor.execute("SELECT id, client, starttime, endtime FROM run ORDER BY starttime", [])
    for runResult in runCursor:

        runNumber += 1
        print ("Run", runNumber, "of", runCount)


        
        (srcRunId, runClient, runStart, runEnd) = runResult

        counterCursor.execute("SELECT COUNT(0) FROM directory WHERE run_id = ?", (srcRunId,))
        dirCount = counterCursor.fetchone()[0]
        print (" -", dirCount, "directories")
        
        counterCursor.execute("SELECT COUNT(0) FROM link WHERE run_id = ?", (srcRunId,))
        linkCount = counterCursor.fetchone()[0]
        print (" -", linkCount, "symbolic links")

        counterCursor.execute("SELECT COUNT(0) FROM file WHERE run_id = ?", (srcRunId,))
        fileCount = counterCursor.fetchone()[0]
        print (" -", fileCount, "files")
        
        dstRunId = runTable.getId(runClient, runStart)
        runTable.updateStatus(dstRunId, "Importing")
        runTable.updateEndtime(dstRunId, runEnd)
        destDB.commit()

        dirNumber = 0
        
        dirCursor = sourceDB.cursor()
        dirCursor.execute("SELECT filepath, fileowner, filegroup, filemode, filetime FROM directory WHERE run_id = ?", (srcRunId,))
        for dirResult in dirCursor:
            dirNumber += 1
            if (dirNumber % 1000 == 0):
                print ("HOST", args.hostname, "RUN", runNumber, "of", runCount, "DIR ", dirNumber, "of", dirCount)
                #destDB.commit()
                
            (filePath, fileOwner, fileGroup, fileMode, fileTime) = dirResult

            dirTable.getId(dstRunId, filePath, fileOwner, fileGroup, fileMode, fileTime)
            
        print ("HOST", args.hostname, "RUN", runNumber, "of", runCount, "DIR ", dirNumber, "of", dirCount)
        destDB.commit()
        
        linkNumber = 0
            
        linkCursor = sourceDB.cursor()
        linkCursor.execute("SELECT filepath, destpath FROM link WHERE run_id = ?", (srcRunId,))
        for linkResult in linkCursor:
            linkNumber += 1
            if (linkNumber % 1000 == 0):
                print ("HOST", args.hostname, "RUN", runNumber, "of", runCount, "LINK", linkNumber, "of", linkCount)
                #destDB.commit()
            
            (filePath, destPath) = linkResult

            linkTable.getId(dstRunId, filePath, destPath)

        print ("HOST", args.hostname, "RUN", runNumber, "of", runCount, "LINK", linkNumber, "of", linkCount)
        destDB.commit()
        
        fileNumber = 0
        
        fileCursor = sourceDB.cursor()
        fileCursor.execute("SELECT f.filepath, f.fileowner, f.filegroup, f.filemode, f.filesize, f.filetime, s.filesha FROM file f JOIN filesha s ON s.id = f.filesha_id WHERE run_id = ?", (srcRunId,))
        for fileResult in fileCursor:
            fileNumber += 1
            if (fileNumber % 1000 == 0):
                print ("HOST", args.hostname, "RUN", runNumber, "of", runCount, "FILE", fileNumber, "of", fileCount)
                #destDB.commit()
                
            (filePath, fileOwner, fileGroup, fileMode, fileSize, fileTime, fileSha) = fileResult

            fileTable.getId(dstRunId, filePath, fileOwner, fileGroup, fileMode, fileSize, fileTime, fileSha)

        print ("HOST", args.hostname, "RUN", runNumber, "of", runCount, "FILE", fileNumber, "of", fileCount)
        destDB.commit()
        
        runTable.updateStatus(dstRunId, "Imported")
        destDB.commit()

main()
