import sys, os
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
import youtube_dl as ydl
from urllib import request
import traceback
import subprocess
import m3u8
import asyncio

api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']

CHAT_WITH_BOT_ID = int(os.environ['CHAT_WITH_BOT_ID'])

client = TelegramClient(os.environ['TG_CLIENT_SESSION_FILE_NAME'], api_id, api_hash)
y = ydl.YoutubeDL({'format': 'best[ext=mp4,height>=720]+best[ext=mp4,height<=360]/best[ext=mp4]'})

TG_MAX_FILE_SIZE = 1500


def video_info(url, use_m3u8=False):
    if use_m3u8:
        m3u8_obj = m3u8.load(url)
        url = m3u8_obj.segments[0].absolute_uri  # override for mediainfo call
        dur = 0
        for s in m3u8_obj.segments:
            if hasattr(s, 'duration'):
                dur += s.duration

    mi_proc = subprocess.Popen(['mediainfo', '--Inform=Video;%Width%\\n%Height%\\n%Duration%', '2>', '/dev/null', url],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    out = mi_proc.stdout.read()
    out = out.split(b'\n')
    w = int(out[0])
    h = int(out[1])
    if use_m3u8:
        dur = int(dur)
    else:
        dur = int(int(out[2])/1000)


    return w, h, dur


def video_size(url):
    head_req = request.Request(url, method='HEAD')
    with request.urlopen(head_req) as resp:
        return int(resp.headers['Content-Length'])


def m3u8_video_size(url):
    m3u8_obj = m3u8.load(url)
    size = 0

    for seg in m3u8_obj.segments:
        head_req = request.Request(seg.absolute_uri, method='HEAD')
        with request.urlopen(head_req) as resp:
            size += int(resp.headers['Content-Length'])

    return size

async def main():
    started = int(sys.argv[1])
    chat_and_message_id = str(sys.argv[2])
    urls = str(sys.argv[3]).split(" ")

    if started != 0:
        print("Already started " + str(sys.argv[1:]))
        await client.connect()


    for u in urls:
        try:
            vinfo = y.extract_info(u, download=False)
        except Exception as e:
            if "Please log in or sign up to view this video" in e.__str__():
                if 'vk.com' in u or 'facebook.com' in u:
                    try:
                        yy = ydl.YoutubeDL({'format': 'best[ext=mp4,height>=720]+best[ext=mp4,height<=360]/best[ext=mp4]', 'username': os.environ['VIDEO_ACCOUNT_USERNAME'], 'password': os.environ['VIDEO_ACCOUNT_PASSWORD']})
                        vinfo = yy.extract_info(u, download=False)
                    except Exception as e:
                        await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                        continue
                else:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                    continue
            elif 'This playlist does not exist' in e.__str__() or 'This playlist is private' in e.__str__():
                try:
                    yy = ydl.YoutubeDL({'format': 'best[ext=mp4,height>=720]+best[ext=mp4,height<=360]/best[ext=mp4]', 'noplaylist': True})
                    vinfo = yy.extract_info(u, download=False)
                except Exception as e:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                    continue
            else:
                await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                continue

        entries = None
        if '_type' in vinfo and vinfo['_type'] == 'playlist':
            entries = vinfo['entries']
        else:
            entries = [vinfo]

        for entry in entries:
            formats = entry.get('requested_formats')
            file_size = None
            chosen_format = None

            if formats is not None:
                for f in formats:
                    if f['protocol'] in ['rtsp', 'rtmp', 'rtmpe', 'mms', 'f4m', 'ism', 'http_dash_segments']:
                        continue
                    if 'm3u8' in f['protocol']:
                        file_size = m3u8_video_size(f['url'])
                    else:
                        file_size = video_size(f['url'])
                    if ('m3u8' in f['protocol'] and file_size / (1024*1024) <= TG_MAX_FILE_SIZE) or (file_size / (1024 * 1024) <= TG_MAX_FILE_SIZE):
                        chosen_format = f
                        break
            else:
                if entry['protocol'] in ['rtsp', 'rtmp', 'rtmpe', 'mms', 'f4m', 'ism', 'http_dash_segments']:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+"ERROR: Failed find suitable video format")
                    return
                if 'm3u8' in entry['protocol']:
                    file_size = m3u8_video_size(entry['url'])
                else:
                    file_size = video_size(entry['url'])
                if ('m3u8' in entry['protocol'] and file_size / (1024*1024) <= TG_MAX_FILE_SIZE) or (file_size / (1024 * 1024) <= TG_MAX_FILE_SIZE):
                    chosen_format = entry

            try:
                file = await client.upload_file(chosen_format['url'], file_name=entry['title'] + '.' + chosen_format['ext'], protocol=chosen_format['protocol'], file_size=file_size)
                if ('duration' not in entry and 'duration' not in chosen_format) or ('width' not in chosen_format) or ('height' not in chosen_format):
                    width, height, duration = video_info(chosen_format['url'], use_m3u8=('m3u8' in chosen_format['protocol']))
                else:
                    width, height, duration = chosen_format['width'], chosen_format['height'], int(entry['duration']) if 'duration' not in entry else int(entry['duration'])

                await client.send_file(CHAT_WITH_BOT_ID, file, video_note=True,
                                       attributes=(DocumentAttributeVideo(duration,
                                                                          width,
                                                                          height,
                                                                          supports_streaming=True),), caption=chat_and_message_id)
            except Exception as e:
                print(e)
                traceback.print_exc()


started = int(sys.argv[1])
if not started:
    client.start()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

