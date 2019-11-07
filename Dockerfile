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
COPY --from=0 /go/src/github.com/kfur/YtbDownBot/life.session .
COPY --from=0 /go/src/github.com/kfur/YtbDownBot/requirements.txt .


RUN apt update && \
    apt install -y mediainfo jq python3 python3-pip git ffmpeg && \
    pip3 install -r requirements.txt  && \
    apt-get autoremove -y && apt-get clean && apt-get autoclean

CMD ["./start.sh"]
