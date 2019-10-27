FROM golang:latest

WORKDIR /go/src/github.com/kfur/YtbDownBot
COPY . .

RUN apt update && apt upgrade -y && \
    apt install -y apt-transport-https curl gnupg && \
    curl "https://repo.zelenin.pw/gpg.key" | apt-key add - && \
    echo "deb [arch=amd64] https://repo.zelenin.pw common contrib" > "/etc/apt/sources.list.d/tdlib.list" && \
    apt update && \
    apt install -y tdlib-dev && \
    go build


FROM ubuntu:19.04

EXPOSE 80

WORKDIR /root/YtbDownBot
COPY --from=0 /go/src/github.com/kfur/YtbDownBot/YtbDownBot .

RUN apt update && apt upgrade -y && \
    apt install -y apt-transport-https curl gnupg && \
    curl "https://repo.zelenin.pw/gpg.key" | apt-key add - && \
    echo "deb [arch=amd64] https://repo.zelenin.pw common contrib" > "/etc/apt/sources.list.d/tdlib.list" && \
    apt update && \
    apt install -y tdlib mediainfo jq && \
    apt-get autoremove -y && apt-get clean && apt-get autoclean

CMD ["./YtbDownBot"]
