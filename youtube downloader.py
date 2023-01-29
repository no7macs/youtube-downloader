from __future__ import unicode_literals
from concurrent.futures import process
from logging import exception
import youtube_dl
import os
import json
import threading
import gc
import sys
import time

dir_path = os.path.dirname(os.path.realpath(__file__))

def execution(sema, processId, processManager):
    def download():
        # class for logging the YTDL outputs
        class YTDLLLogger(object):
            def __init__(self, processId) -> None:
                self.processId = processId
            def debug(self, msg) -> None:
                processManager.setLogMessage(self.processId, "debug", msg)
            def warning(self, msg) -> None:
                processManager.setLogMessage(self.processId, "warning", msg)
            def error(self, msg) -> None:
                processManager.setLogMessage(self.processId, "error", msg)
        # progress and current download info
        folder = processManager.getProcessById(processId)[1]
        def progressHook(d):
            processManager.setProcessStatus(processId, body = d)
        # make extra sub directories
        os.makedirs(f"""{dir_path}/{folder}""", exist_ok=True)
        os.makedirs(f"""{dir_path}/{folder}/temp""", exist_ok=True)
        with open(f"""{dir_path}/{folder}/archive.txt""", mode='a'): pass
        # youtube-dl confis
        outDir = dir_path
        ydl_opts = {
                    'format': 'bestvideo+bestaudio',
                    'outtmpl':f"""{outDir}/{folder}/%(title)s-%(id)s.%(ext)s""",
                    'download_archive':f'{outDir}/{folder}/archive.txt',
                    'cachedir':f"""{outDir}/{folder}/cache""",
                    'write-description':True,
                    'cookiefile':'./youtube.com_cookies.txt',
                    'merge_output_format':'mkv',
                    'logger': YTDLLLogger(processId),
                    'progress_hooks': [progressHook],
                    }
        # download videos
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([processManager.getProcessById(processId)[3]])
        except Exception as a:
            print(a)
            download()
        #return after finishing
        return()
    # get sema and mark running value as true
    sema.acquire()
    processManager.setProcessSemaStatus(processId, True)
    download()
    '''
    if processManager.getProcessById(processId)[2] == False:
        print("checkingsema")
        sema.acquire()
        processManager.setProcessSemaStatus(processId, True)
    else: pass
    '''
    sema.release()
    gc.collect()
    '''
    # remove big webm
    webmFiles = os.listdir(f"""./{folder}/webm/""")
    for b in webmFiles:
        if os.path.getsize(f"./{folder}/webm/{b}") >= (1024*1024)*6:
            os.remove(f"""./{folder}/webm/{b}""")
    '''


class processListManager():
    def __init__(self) -> None:
        self.processThreadLock = threading.Lock()
        # processNum, sourceName, semaStatus, urlLoc, YTDLStatus, logMessages(debug, warning, error)
        self.processList: list = []
        self.processNum = 0
        self.processListCache: dict = {"id":{}, "name":{}, "semaStatus":{"True":[], "False":[]}}
        gc.collect()

    def buildProcessList(self, sourcesFileLoc: str) -> None:
        with self.processThreadLock:
            self.processList = []
            self.processNum = 0
            with open(sourcesFileLoc, 'r') as jsonRaw:
                jsonDat =  json.load(jsonRaw)
            for a in jsonDat:
                self.processNum += 1
                self.processList.append([self.processNum, a, False, jsonDat[a], {}, {"debug":"", "warning":"", "error":""}])

    def cacheProcessList(self) -> None:
        with self.processThreadLock:
            self.processListCache = {"id":{}, "name":{}, "semaStatus":{"True":[], "False":[]}}
            for a, b in enumerate(self.processList):
                self.processListCache["name"][b[1]] = a
                self.processListCache["semaStatus"][str(b[2])].append(a)
                self.processListCache["id"][b[0]] = a
            #by json dat
            #by ytdl status
            #by error codes
    
    def getProcessNum(self) -> int:
        with self.processThreadLock:
            return(len(self.processList))

    def getFullProcessList(self) -> list:
        with self.processThreadLock:
            for a in self.processList:
                yield(a)

    def getProcessById(self, processId: int) -> list:
        return(self.processList[self.processListCache["id"][processId]])

    def getProcessByIndex(self, index: int) -> list:
        return(self.processList[index])

    def getProcessByName(self, name: str) -> list:
        return(self.processList[self.processListCache["name"][name]])

    def setProcessSemaStatus(self, processId: int, semaStatus: bool) -> None:
        with self.processThreadLock:
            workingProcess = self.getProcessById(processId)
            workingProcess[2] = semaStatus

    def setLogMessage(self, processId: int, msg: str, body: str) -> None:
        with self.processThreadLock:
            workingProcess = self.getProcessById(processId)
            workingProcess[5][msg] = body
    
    def setProcessStatus(self, processId: int, body: str) -> None:
        with self.processThreadLock:
            workingProcess = self.getProcessById(processId)
            workingProcess[4] = body


if __name__ == "__main__":
    semaphoreSize = 8
    processManager = processListManager()
    processManager.buildProcessList(dir_path + '/sources.json')
    processManager.cacheProcessList()
    # start all threads
    sema = threading.Semaphore(semaphoreSize)
    for c in range(0, processManager.getProcessNum()):
        processId = processManager.getProcessByIndex(c)[0]
        p = threading.Thread(target=execution, args = (sema, processId, processManager), name=processId)
        p.start()