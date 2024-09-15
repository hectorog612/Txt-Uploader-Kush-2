import os
import time
import datetime
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import tgcrypto
import subprocess
import concurrent.futures

from utils import progress_bar
from pyrogram import Client, filters
from pyrogram.types import Message

logging.basicConfig(level=logging.INFO)

def duration(filename):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    return float(result.stdout)

def exec(cmd):
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.stdout.decode()
        logging.info(output)
        return output
    except Exception as e:
        logging.error(f"Error executing command {cmd}: {e}")
        return None

def pull_run(work, cmds):
    with concurrent.futures.ThreadPoolExecutor(max_workers=work) as executor:
        logging.info("Waiting for tasks to complete")
        executor.map(exec, cmds)

async def aio(url, name):
    k = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(k, mode='wb') as f:
                    await f.write(await resp.read())
    return k

async def download(url, name):
    ka = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(ka, mode='wb') as f:
                    await f.write(await resp.read())
    return ka

def parse_vid_info(info):
    info = info.strip().split("\n")
    new_info = []
    temp = []
    for i in info:
        i = str(i).strip()
        if "[" not in i and '---' not in i:
            i = ' '.join(i.split())
            i = i.split("|")[0].split(" ", 2)
            try:
                if "☢ 𝐑𝐄𝐒𝐎𝐋𝐔𝐓𝐈𝐎𝐍 ☢" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info.append((i[0], i[2]))
            except IndexError:
                pass
    return new_info

def vid_info(info):
    info = info.strip().split("\n")
    new_info = {}
    temp = []
    for i in info:
        i = str(i).strip()
        if "[" not in i and '---' not in i:
            i = ' '.join(i.split())
            i = i.split("|")[0].split(" ", 3)
            try:
                if "☢ 𝐑𝐄𝐒𝐎𝐋𝐔𝐓𝐈𝐎𝐍 ☢" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info[i[2]] = i[0]
            except IndexError:
                pass
    return new_info

async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    logging.info(f'[{cmd!r} exited with {proc.returncode}]')
    if proc.returncode != 0:
        logging.error(stderr.decode())
        return False
    return stdout.decode() if stdout else stderr.decode()

def old_download(url, file_name, chunk_size=1024 * 10):
    if os.path.exists(file_name):
        os.remove(file_name)
    r = requests.get(url, allow_redirects=True, stream=True)
    with open(file_name, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
    return file_name

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.strftime("%H%M%S")
    return f"{date} {current_time}.mp4"

async def download_video(url, cmd, name):
    download_cmd = f'{cmd} -R 25 --fragment-retries 25 --external-downloader aria2c --downloader-args "aria2c: -x 16 -j 32"'
    global failed_counter
    logging.info(download_cmd)
    k = subprocess.run(download_cmd, shell=True)
    if "visionias" in cmd and k.returncode != 0 and failed_counter <= 10:
        failed_counter += 1
        await asyncio.sleep(5)
        await download_video(url, cmd, name)
    failed_counter = 0
    try:
        if os.path.isfile(name):
            return name
        if os.path.isfile(f"{name}.webm"):
            return f"{name}.webm"
        name = name.split(".")[0]
        if os.path.isfile(f"{name}.mkv"):
            return f"{name}.mkv"
        if os.path.isfile(f"{name}.mp4"):
            return f"{name}.mp4"
        if os.path.isfile(f"{name}.mp4.webm"):
            return f"{name}.mp4.webm"
        return name
    except FileNotFoundError:
        return os.path.splitext(name)[0] + ".mp4"

async def send_doc(bot: Client, m: Message, cc, ka, cc1, prog, count, name):
    reply = await m.reply_text(f"☢𝗨𝗣𝗟𝗢𝗔𝗗𝗜𝗡𝗚 𝗩𝗜𝗗𝗘𝗢☢ `{name}`")
    time.sleep(1)
    start_time = time.time()
    await m.reply_document(ka, caption=cc1)
    count += 1
    await reply.delete()
    time.sleep(1)
    os.remove(ka)
    time.sleep(3)

async def send_vid(bot: Client, m: Message, cc, filename, thumb, name, prog):
    subprocess.run(f'ffmpeg -i "{filename}" -ss 00:01:00 -vframes 1 "{filename}.jpg"', shell=True)
    await prog.delete()
    reply = await m.reply_text(f"**☢𝗨𝗣𝗟𝗢𝗔𝗗𝗜𝗡𝗚 𝗩𝗜𝗗𝗘𝗢☢** ➤ `{name}`")
    try:
        thumbnail = thumb if thumb != "no" else f"{filename}.jpg"
    except Exception as e:
        await m.reply_text(str(e))

    dur = int(duration(filename))
    start_time = time.time()

    try:
        await m.reply_video(filename, caption=cc, supports_streaming=True, height=720, width=1280, thumb=thumbnail, duration=dur, progress=progress_bar, progress_args=(reply, start_time))
    except Exception:
        await m.reply_document(filename, caption=cc, progress=progress_bar, progress_args=(reply, start_time))
    os.remove(filename)
    os.remove(f"{filename}.jpg")
    await reply.delete()
