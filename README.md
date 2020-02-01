# YtbDownBot
Telegram bot that utilize youtube-dl functionality for downloading video directly to telegram.
Simple clone of https://t.me/VideoTubeBot.

# Dependencies
Install `ffmpeg`, `mediainfo` and `python3`.

Python3 dependencies install via `pip3 install -r requirements.txt`
# Running
For running required phone number for bypassing telegram bot api upload files limitation to 50 MB.

Set the following enviroment variables:
  1. Bot token(from Bot Father):
`BOT_API_TOKEN`

  2. Chat id between bot and agent (regular client with phone number 
for bypass limit in 50MB):
`BOT_AGENT_CHAT_ID`

  3. Chat id between agent(regular client with phone number 
for bypass limit in 50MB) and bot:
`CHAT_WITH_BOT_ID`

  4. Api id (https://core.telegram.org/api/obtaining_api_id):
`API_ID`
  5. Api hash (https://core.telegram.org/api/obtaining_api_id):
`API_HASH`
  6. Telegram client session string for telethon StringSession:
  `CLIENT_SESSION`

Build by:
`go build`

Run by:
`./YtbDownBot`
