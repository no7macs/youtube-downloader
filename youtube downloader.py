from __future__ import unicode_literals
from concurrent.futures import process
from logging import exception
import youtube_dl
import os
import json
import threading
import gc

def execution(sema, folder, link, processInfo):
    # get sema and mark running value as true
    sema.acquire()
    processInfo[0] = True
    # class for logging the YTDL outputs
    class YTDLLLogger(object):
        def __init__(self, processInfo):
            self.processInfo = processInfo
        def debug(self, msg):
            self.processInfo[2]["debug"] = msg
        def warning(self, msg):
            self.processInfo[2]["warning"] = msg
        def error(self, msg):
            self.processInfo[2]["error"] = msg
    # progress and current download info
    def progressHook(d):
        processInfo[1] = d

    os.makedirs(f"""./{folder}""", exist_ok=True)
    os.makedirs(f"""./{folder}/temp""", exist_ok=True)
    os.makedirs(f"""./{folder}/webm""", exist_ok=True)
    os.makedirs(f"""./{folder}/mp4""", exist_ok=True)
    with open(f"""./{folder}/archive.txt""", mode='a'): pass

    ydl_opts = {
                'format': 'bestvideo+bestaudio',
                'outtmpl':f"""{folder}/%(title)s-%(id)s.%(ext)s""",
                'download_archive':f'./{folder}/archive.txt',
                'cachedir':f"""./{folder}/cache""",
                'cookiefile':'./youtube.com_cookies.txt',
                'merge_output_format':'mkv',
                'logger': YTDLLLogger(processInfo),
                'progress_hooks': [progressHook],
                }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])
    sema.release()
    gc.collect()
    # remove big webm
    webmFiles = os.listdir(f"""./{folder}/webm/""")
    for b in webmFiles:
        if os.path.getsize(f"./{folder}/webm/{b}") >= (1024*1024)*6:
            os.remove(f"""./{folder}/webm/{b}""")

if __name__ == "__main__":
        with open('sources.json', 'r') as jsonRaw:
            jsonDat =  json.load(jsonRaw)
            process_list = {}
        sema = threading.Semaphore(8)
        for a in jsonDat:
            process_list[a] = [False, {}, {"debug":"", "warning":"", "error":""}]
            p = threading.Thread(target=execution, args = (sema, a, jsonDat[a], process_list[a]), name=a)
            p.start()
        gc.collect()