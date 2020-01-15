FROM golang:latest

WORKDIR /go/src/github.com/kfur/YtbDownBot
COPY . .

RUN go build


FROM ubuntu:19.04

EXPOSE 80

WORKDIR /root/YtbDownBot
COPY --from=0 /go/src/github.com/kfur/YtbDownBot/YtbDownBot .
COPY --from=0 /go/src/github.com/kfur/YtbDownBot/start.sh .
COPY --from=0 /go/src/github.com/kfur/YtbDownBot/main.py .
COPY --from=0 /go/src/github.com/kfur/YtbDownBot/requirements.txt .

ADD youtubedl-autoupdate /etc/cron.daily/youtubedl 

RUN apt update && \
    apt install -y mediainfo jq python3 python3-pip git ffmpeg cron && \
    pip3 install -r requirements.txt  && \
    chmod +x /etc/cron.daily/youtubedl && \
    touch /var/log/cron.log && \
    apt-get autoremove -y && apt-get clean && apt-get autoclean

ARG ARG_BOT_API_TOKEN
ARG ARG_BOT_AGENT_CHAT_ID
ARG ARG_API_ID
ARG ARG_API_HASH
ARG ARG_CHAT_WITH_BOT_ID
ARG ARG_CLIENT_SESSION
ARG ARG_VIDEO_ACCOUNT_USERNAME
ARG ARG_VIDEO_ACCOUNT_PASSWORD

ENV BOT_API_TOKEN $ARG_BOT_API_TOKEN
ENV BOT_AGENT_CHAT_ID $ARG_BOT_AGENT_CHAT_ID
ENV API_ID $ARG_API_ID
ENV API_HASH $ARG_API_HASH
ENV CHAT_WITH_BOT_ID $ARG_CHAT_WITH_BOT_ID
ENV CLIENT_SESSION $ARG_CLIENT_SESSION
ENV VIDEO_ACCOUNT_USERNAME $ARG_VIDEO_ACCOUNT_USERNAME
ENV VIDEO_ACCOUNT_PASSWORD $ARG_VIDEO_ACCOUNT_PASSWORD

CMD ["./start.sh"]
