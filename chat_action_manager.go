package main

import (
	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api"
	log "github.com/sirupsen/logrus"
	"sync"
	"time"
)

type ChatAction struct {
	tgbotapi.ChatActionConfig
	Count int
}

type ChatActionManager struct {
	ChatActionList []ChatAction
	Lock sync.Mutex
}

func (cal *ChatActionManager) ActionLoop()  {
	for {
		cal.Lock.Lock()
		var err error
		for i := range cal.ChatActionList {
			_, err = Bot.Send(cal.ChatActionList[i])
			if err != nil {
				log.Errorf("Failed update chat action for %d; %s", cal.ChatActionList[i], err)
			}
		}
		cal.Lock.Unlock()
		time.Sleep(time.Second*2)
	}
}

func (cal *ChatActionManager) AddAction(ca tgbotapi.ChatActionConfig)  {
	cal.Lock.Lock()
	defer cal.Lock.Unlock()
	for i := range cal.ChatActionList {
		if cal.ChatActionList[i].ChatID == ca.ChatID {
			cal.ChatActionList[i].Count++
			return
		}
	}

	cal.ChatActionList = append(cal.ChatActionList, ChatAction{ca, 1})
}

func (cal *ChatActionManager) DelAction(chatID int64)  {
	cal.Lock.Lock()
	defer cal.Lock.Unlock()
	for i := range cal.ChatActionList {
		if cal.ChatActionList[i].ChatID == chatID {
			if cal.ChatActionList[i].Count <= 1 {
				cal.ChatActionList[i] = cal.ChatActionList[len(cal.ChatActionList)-1]
				cal.ChatActionList = cal.ChatActionList[:len(cal.ChatActionList)-1]
			} else {
				cal.ChatActionList[i].Count--
			}
			return
		}
	}
}