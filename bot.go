package main

import (
	"fmt"
	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api"
	"os/exec"
	"os"
	"sync"

	log "github.com/sirupsen/logrus"
	"mvdan.cc/xurls"
	"strconv"
	"strings"
)

var Bot *tgbotapi.BotAPI
var UploadProcsCond *sync.Cond
var UploadProcsLock sync.Mutex

func init() {
	var err error
	Bot, err = tgbotapi.NewBotAPI(os.Getenv("BOT_API_TOKEN"))
	if err != nil {
		log.Panic(err)
	}

	UploadProcsCond = sync.NewCond(&UploadProcsLock)

	log.Printf("Authorized on account %s", Bot.Self.UserName)

	BotAgentChatID, _ = strconv.ParseInt(os.Getenv("BOT_AGENT_CHAT_ID"), 10, 64)
}

// Chat id with agent(client that used for bypass limit in 50MB)
var BotAgentChatID int64

func BotMainLoop() {
	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60
	updates, err := Bot.GetUpdatesChan(u)
	if err != nil {
		log.Panic(err)
	}

	var lastInfoMsg tgbotapi.Message
	rxRelaxed := xurls.Relaxed()

	for update := range updates {
		if update.Message == nil { // ignore any non-Message Updates
			continue
		}
		if update.Message.IsCommand() {
			if update.Message.Command() == "ping" {
				Bot.Send(tgbotapi.NewMessage(update.Message.Chat.ID, "pong"))
				continue
			}
			if update.Message.Command() == "start" {
				continue
			}
		}

		// client sended to us video
		if update.Message.Chat.ID == BotAgentChatID {
			if update.Message.Video == nil && update.Message.Text != "" {
				// check is message contain error string
				splitedText := strings.Split(update.Message.Text, " ")
				chatID, err := strconv.ParseInt(splitedText[0], 10, 64)
				if err == nil {
					// delete old info msg
					_, err = Bot.DeleteMessage(tgbotapi.NewDeleteMessage(chatID, lastInfoMsg.MessageID))
					if err != nil {
						log.Error(err)
					}
					Bot.Send(tgbotapi.NewMessage(chatID, strings.Join(splitedText[1:], " ")))
					continue
				}
			} else {
				chatIDStr := update.Message.Caption
				chatID, _ := strconv.ParseInt(chatIDStr, 10, 64)

				// delete old info msg
				_, err = Bot.DeleteMessage(tgbotapi.NewDeleteMessage(chatID, lastInfoMsg.MessageID))
				if err != nil {
					log.Error(err)
				}

				ShareVideoFile(chatID, update.Message.Video)
				continue
			}

		}

		urls := rxRelaxed.FindAllString(update.Message.Text, 10)
		if len(urls) == 0 {
			Bot.Send(tgbotapi.NewMessage(update.Message.Chat.ID, "There aren't any urls in your message.\n Please send at least one."))
			continue
		} else {
			lastInfoMsg, err = Bot.Send(tgbotapi.NewMessage(update.Message.Chat.ID, "Uploading..."))
		}

		log.Info("Message is ", update.Message.Text)

		go func(urls []string, chatID int64) {
			err = RequestHanlder(urls, chatID)
			if err != nil {
				log.Error(err)
				Bot.Send(tgbotapi.NewMessage(update.Message.Chat.ID, "Failed download video"))
			}
		}(Deduplicate(urls), update.Message.Chat.ID)

	}
}

const MAX_UPLOAD_PROCS = 10
var CurrentUploadProcs = 0

func RequestHanlder(urls []string, fromChatID int64) error {
	UploadProcsLock.Lock()

	var OneInstanceAlreadyRan = 0

	for CurrentUploadProcs >= MAX_UPLOAD_PROCS {
		fmt.Printf("Wait for free procs (Currently running procs: %d)\n", CurrentUploadProcs)
		UploadProcsCond.Wait()
	}
	if CurrentUploadProcs != 0 {
		OneInstanceAlreadyRan = 1
	}
	CurrentUploadProcs += 1
	urlsArg := strings.Join(urls," ")
	p := fmt.Sprintf(`python3 ./main.py %d %d '%s'`, OneInstanceAlreadyRan, fromChatID, urlsArg)
	uploadCmd := exec.Command("bash", "-c", fmt.Sprintf(`python3 ./main.py %d %d '%s'`, OneInstanceAlreadyRan, fromChatID, urlsArg))

	UploadProcsLock.Unlock()
	out, err := uploadCmd.Output()
	if err != nil {
		fmt.Println(p, " ", err)
	}
	fmt.Println(p, " ", string(out))

	UploadProcsLock.Lock()
	CurrentUploadProcs -= 1
	UploadProcsLock.Unlock()

	UploadProcsCond.Broadcast()
	if err != nil {
		fmt.Println(err)
	}

	return nil
}

func ShareVideoFile(chatID int64, video *tgbotapi.Video) {
	log.Info("share video")
	vidShare := tgbotapi.NewVideoShare(chatID, video.FileID)
	_, err := Bot.Send(vidShare)
	if err != nil {
		log.Error(err)
	}
}

// Deduplicate returns a new slice with duplicates values removed.
func Deduplicate(s []string) []string {
	if len(s) <= 1 {
		return s
	}

	result := []string{}
	seen := make(map[string]struct{})
	for _, val := range s {
		if _, ok := seen[val]; !ok {
			result = append(result, val)
			seen[val] = struct{}{}
		}
	}
	return result
}