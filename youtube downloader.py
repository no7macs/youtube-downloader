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
    # make extra sub directories
    os.makedirs(f"""./{folder}""", exist_ok=True)
    os.makedirs(f"""./{folder}/temp""", exist_ok=True)
    os.makedirs(f"""./{folder}/webm""", exist_ok=True)
    os.makedirs(f"""./{folder}/mp4""", exist_ok=True)
    with open(f"""./{folder}/archive.txt""", mode='a'): pass
    # youtube-dl confis
    outDir = dir_path
    ydl_opts = {
                'format': 'bestvideo+bestaudio',
                'outtmpl':f"""{outDir}/{folder}/%(title)s-%(id)s.%(ext)s""",
                'download_archive':f'{outDir}/{folder}/archive.txt',
                'cachedir':f"""{outDir}/{folder}/cache""",
                'cookiefile':'./youtube.com_cookies.txt',
                'merge_output_format':'mkv',
                'logger': YTDLLLogger(processInfo),
                'progress_hooks': [progressHook],
                }
    # download videos
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
    except:
        processInfo[2]["error"] = "youtube-dl crashed and burned"
        execution(sema, folder, link, processInfo)
    # release sema, garbage collect
    sema.release()
    gc.collect()

    # remove big webm
    webmFiles = os.listdir(f"""./{folder}/webm/""")
    for b in webmFiles:
        if os.path.getsize(f"./{folder}/webm/{b}") >= (1024*1024)*6:
            os.remove(f"""./{folder}/webm/{b}""")

if __name__ == "__main__":
    semaphoreSize = 8
    with open(dir_path + '/sources.json', 'r') as jsonRaw:
        jsonDat =  json.load(jsonRaw)
        process_list = {}
    sema = threading.Semaphore(semaphoreSize)
    for a in jsonDat:
        process_list[a] = [False, {}, {"debug":"", "warning":"", "error":""}]
        p = threading.Thread(target=execution, args = (sema, a, jsonDat[a], process_list[a]), name=a)
        p.start()
    while True:
        #print(process_list["Action Movie FX"][1])
        terminalOut = ""
        if len(process_list) > 0:
            for b in process_list:
                if len(process_list[b][1]) > 0 and (not process_list[b][1]["status"] == 'finished'):
                    terminalOut += ''.join([
                        f"""{b}\r\n""",
                        f"""    {process_list[b][1]["filename"]}\r\n""",
                        f"""    {process_list[b][1]["_percent_str"]}\r\n""",
                        f"""    {process_list[b][1]["_speed_str"]}\r\n""",
                        f"""    {process_list[b][1]["_eta_str"]}\r\n""",
                        f"""{process_list[b][2]["error"]}\r\n"""
                    ])
                else:
                    sys.stdout.write("Starting downloads...\r\n")
        else: 
            sys.stdout.write("Starting first process...\r\n")
        sys.stdout.write(terminalOut)
        time.sleep(0.5)
        sys.stdout.flush()
        os.system('cls')
