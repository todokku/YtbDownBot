package main

import (
	"fmt"
	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api"
	"mvdan.cc/xurls"
	"os/exec"
	"os"

	log "github.com/sirupsen/logrus"
	"strconv"
	"strings"
)

var Bot *tgbotapi.BotAPI

var ChatActionHandler ChatActionManager

func init() {
	var err error
	Bot, err = tgbotapi.NewBotAPI(os.Getenv("BOT_API_TOKEN"))
	if err != nil {
		log.Panic(err)
	}

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

	//var lastInfoMsg tgbotapi.Message
	rxRelaxed := xurls.Relaxed()

	go ChatActionHandler.ActionLoop()

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
				Bot.Send(tgbotapi.NewMessage(update.Message.Chat.ID, "Send me a video links"))
				continue
			}
		}

		// client sended to us video
		if update.Message.Chat.ID == BotAgentChatID {
			if update.Message.Video == nil && update.Message.Text != "" {
				//No video then error occured
				// check is message contain error string
				splitedText := strings.Split(update.Message.Text, " ")
				var chatID int64
				var messageID int
				if strings.Contains(splitedText[0], ":") {
					captionWithID := strings.Split(splitedText[0], ":")
					chatID, _ = strconv.ParseInt(captionWithID[0], 10, 64)
					messageID, _ = strconv.Atoi(captionWithID[1])
				} else {
					chatID, err = strconv.ParseInt(splitedText[0], 10, 64)
				}

				if err == nil {
					errMsg := tgbotapi.NewMessage(chatID, strings.Join(splitedText[1:], " "))
					if messageID != 0 {
						errMsg.ReplyToMessageID = messageID
					}
					Bot.Send(errMsg)
					continue
				}
			} else {
				// All good video was received
				caption := strings.Split(update.Message.Caption, ":")
				chatID, _ := strconv.ParseInt(caption[0], 10, 64)
				messageID, _ := strconv.Atoi(caption[1])
				if update.Message.Video != nil {
					ShareVideoFile(update.Message.Video, chatID, messageID)
				} else if update.Message.Document != nil {
					ShareDocumentFile(update.Message.Document, chatID, messageID)
				}
				continue
			}

		}

		urls := rxRelaxed.FindAllString(update.Message.Text, 10)
		if len(urls) == 0 {
			Bot.Send(tgbotapi.NewMessage(update.Message.Chat.ID, "There aren't any urls in your message.\n Please send at least one."))
			continue
		}
		log.Info("Message is ", update.Message.Text)
		go func(urls []string, chatID int64, messageID int) {
			ChatActionHandler.AddAction(tgbotapi.NewChatAction(chatID, "upload_video"))

			err = RequestHanlder(urls, strconv.FormatInt(chatID,10) + ":" + strconv.Itoa(messageID))
			if err != nil {
				log.Error("Request failed: ", err)
				Bot.Send(tgbotapi.NewMessage(update.Message.Chat.ID, "Failed download video"))
			}
			ChatActionHandler.DelAction(chatID)
		}(Deduplicate(urls), update.Message.Chat.ID, update.Message.MessageID)

	}
}


func RequestHanlder(urls []string, chatNmessageID string) error {
	urlsArg := strings.Join(urls," ")
	p := fmt.Sprintf(`python3 ./main.py %s '%s'`, chatNmessageID, urlsArg)
	uploadCmd := exec.Command("bash", "-c", fmt.Sprintf(`python3 ./main.py %s '%s' 2>&1`, chatNmessageID, urlsArg))

	out, err := uploadCmd.Output()
	if err != nil {
		fmt.Println(err)
	}
	fmt.Println(p, " ", string(out))

	return nil
}

func ShareVideoFile(video *tgbotapi.Video, chatID int64, replyToMessageID int) {
	log.Info("share video")
	vidShare := tgbotapi.NewVideoShare(chatID, video.FileID)
	vidShare.ReplyToMessageID = replyToMessageID
	_, err := Bot.Send(vidShare)
	if err != nil {
		log.Error(err)
	}
}

func ShareDocumentFile(doc *tgbotapi.Document, chatID int64, replyToMessageID int) {
	log.Info("share doc")
	docShare := tgbotapi.NewDocumentShare(chatID, doc.FileID)
	docShare.ReplyToMessageID = replyToMessageID
	_, err := Bot.Send(docShare)
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
