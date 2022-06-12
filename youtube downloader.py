from concurrent.futures import process
from logging import exception
import os
import subprocess
import json
import datetime
import time 
import json 
import threading
import random
import gc
import itertools

def execution(sema, folder, link):

    sema.acquire()
    print("Starting, " + folder)

    os.makedirs(f"""./{folder}""", exist_ok=True)
    os.makedirs(f"""./{folder}/temp""", exist_ok=True)
    os.makedirs(f"""./{folder}/webm""", exist_ok=True)

    # download all videos
    #--merge-output-format mkv --all-subs --write-description --write-info-json --write-annotations --all-subs --write-all-thumbnails
    #--embed-subs --embed-thumbnail --add-metadata --prefer-ffmpeg
    #-x -c -k
    os.system(f"""youtube-dl -f bestvideo+bestaudio -o "{folder}/%(title)s-%(id)s.%(ext)s" --add-metadata --embed-subs \
    --cookies "./youtube.com_cookies.txt" --merge-output-format mkv \
    "{link}" """)
    gc.collect()

    # make webm
    files = os.listdir(f"""./{folder}/""")
    for a in files:
        if os.path.splitext(a)[1] == '.mkv':
            result = subprocess.check_output(
                    f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "./{folder}/{a}"',
                    shell=True).decode()
            fields = json.loads(result)['streams'][0]
            duration = fields['tags']['DURATION']
            fps = fields['r_frame_rate']
            date_time_obj = datetime.datetime.strptime(duration.split('.')[0], '%X')
            print(date_time_obj.second)
            if date_time_obj.minute < 2:
                full_file_path = f"""./{folder}/{a}"""
                #{(os.path.getsize(full_file_path)*1024)/date_time_obj.second}
                try:
                    os.system(f"""ffmpeg -i "{full_file_path}" -c:v libvpx -b:v {(5243000)/date_time_obj.second} -pass 1 -an -f -n  "./{folder}/temp/" """)
                    os.system(f"""ffmpeg -i "{full_file_path}" -c:v libvpx -b:v {(5243000)/date_time_obj.second} -preset veryslow -pass 2 -c:a libopus -n "./{folder}/webm/{os.path.splitext(a)[0]}.webm" """)
                    time.sleep(2)
                except Exception as error:
                    print("ffmpeg webm encode error \n" + str(error))
                    os.remove(full_file_path)
    gc.collect()

    # remove big webm
    webmFiles = os.listdir(f"""./{folder}/webm/""")
    for b in webmFiles:
        if os.path.getsize(f"./{folder}/webm/{b}") >= (1024*1024)*6:
            os.remove(f"""./{folder}/webm/{b}""")

    sema.release()

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

    sema = threading.Semaphore(4)
    for a in jsonDat:
        p = threading.Thread(target=execution, args = (sema, a, jsonDat[a]), name=a)
        p.start()