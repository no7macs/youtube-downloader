from __future__ import unicode_literals
from concurrent.futures import process
from logging import exception
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import youtube_dl
import os
import json
import threading
import gc
import asyncio

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

#TODO: run the http server in a thread so the main line of execution doesn't get taken up by it
class httpServer(BaseHTTPRequestHandler):
    def _set_response(self, code) -> None:
        self.send_response(code)
        self.send_header('Content-type', 'text/json')
        self.end_headers()
        
    def do_GET(self):
        self.functionPath = urlparse(self.path).path
        # make sure it's a getter function and get it, other wirse throw an error and return a 400 code
        try:
            if self.functionPath[1:4] == "get":
                self.tempFunc = getattr(processManager, self.functionPath[1:])
            else:
                raise AttributeError("not a getter")
        except AttributeError as err:
            self._set_response(400)
            print(err)
        # format attributes as dictionary
        self.attributeQuery = parse_qs(urlparse(self.path).query)
        # turn into the right value types to be lobbed at processListManager
        for a in self.attributeQuery:
            if self.attributeQuery[a][0].isdigit() == True:
                self.attributeQuery[a] = int(self.attributeQuery[a][0])
            elif self.attributeQuery[a][0].lower() in ["true", "false"]:
                self.attributeQuery[a] = bool(self.attributeQuery[a][0])
            elif self.attributeQuery[a][0].isdigit() == False:
                self.attributeQuery[a] = str(self.attributeQuery[a][0])
        self.getReturn = self.tempFunc(**self.attributeQuery)
        self._set_response(200)
        self.wfile.write(json.dumps(self.getReturn).encode("UTF-8"))

    def do_POST(self):
        #get the path, turn it into the right function, and make sure everything is right
        self.path = urlparse(self.path).path
        try:
            if self.path[1:4] == "set":
                self.tempFunc = getattr(processManager, self.path[1:])
            else:
                raise AttributeError("not a setter")
        except AttributeError as err:
            self._set_response(400)
            print(err)
        self.postData = json.loads((self.rfile.read(int(self.headers['Content-Length']))).decode())
        self.setReturn = self.tempFunc(**self.postData)
        self._set_response(200)
        self.wfile.write(json.dumps(self.setReturn).encode("UTF-8"))
        #TODO: have post calls return modified data when the function doesn't have a return itself
         

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
    
    #TODO: make asyncronous so it can run autonomously
    def cacheProcessList(self) -> None:
        with self.processThreadLock:
            self.processListCache = {"id":{}, "name":{}, "semaStatus":{"True":[], "False":[]}}
            for a, b in enumerate(self.processList):
                self.processListCache["name"][b[1]] = a
                self.processListCache["semaStatus"][str(b[2])].append(a)
                self.processListCache["id"][b[0]] = a
    
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

    #TODO: checks if port is open, if not scan for the lowest open between 1024-49151
    hostName = "localhost"
    serverPort = 8000
    httpBackend = HTTPServer((hostName, serverPort), httpServer)
    httpBackend.serve_forever()