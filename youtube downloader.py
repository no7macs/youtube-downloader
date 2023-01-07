from __future__ import unicode_literals
from concurrent.futures import process
from logging import exception
import youtube_dl
import os
import subprocess
import json
import datetime
import time 
import threading
import gc
import itertools

def execution(sema, folder, link):

    sema.acquire()
    print("Starting, " + folder)

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
                'merge_output_format':'mkv'
                }
    try:       
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
    except:
        execution(sema, folder, link)


    # download all videos
    #--all-subs --write-description --write-info-json --write-annotations --all-subs --write-all-thumbnails
    #--embed-subs --embed-thumbnail --prefer-ffmpeg
    #-x -c -k
    #os.system(f"""youtube-dl -f bestvideo+bestaudio -o "{folder}/%(title)s-%(id)s.%(ext)s" --add-metadata --embed-subs \
    #--cookies "./youtube.com_cookies.txt" --merge-output-format mkv \
    #"{link}" """)
    gc.collect()

    sema.release()
    gc.collect()

    # remove big webm
    webmFiles = os.listdir(f"""./{folder}/webm/""")
    for b in webmFiles:
        if os.path.getsize(f"./{folder}/webm/{b}") >= (1024*1024)*6:
            os.remove(f"""./{folder}/webm/{b}""")

if __name__ == "__main__":
    while True:
        with open('sources.json', 'r') as jsonRaw:
            jsonDat =  json.load(jsonRaw)

            process_list = []
            #shuffle_list = random.shuffle(list(jsonDat.keys()))
            """
            while not len(list(jsonDat.keys())) == 0:
                folder = list(jsonDat.keys())[0]
                if len(process_list) < 4:
                    link = jsonDat[folder]
                    process_list.append(str(random.randint(0,999)))
                    p = threading.Thread(target=execution, args = (sema, folder, link), name=process_list[len(process_list)-1])
                    p.daemon = True
                    process_list[len(process_list)-1] = p
                    print(p)
                    p.start()
                    jsonDat.pop(folder)
                    #process_list[:] = [itertools.filterfalse(, process_list)]
            """

            sema = threading.Semaphore(8)
            for a in jsonDat:
                p = threading.Thread(target=execution, args = (sema, a, jsonDat[a]), name=a)
                p.start()
        gc.collect()