package main

import (
	"fmt"
	"github.com/Arman92/go-tdlib"
	"log"
	"strconv"
)

var TgClient *tdlib.Client
var DeleteMsgsEventListener tdlib.EventReceiver

// chat id between agent and bot
const AgentChatId = 794633388

func init() {
	tdlib.SetLogVerbosityLevel(1)
	// Create new instance of TgClient
	TgClient = tdlib.NewClient(tdlib.Config{
		APIID:               "94575",
		APIHash:             "a3406de8d171bb422bb6ddf3bbd800e2",
		SystemLanguageCode:  "en",
		DeviceModel:         "Server",
		SystemVersion:       "1.0.0",
		ApplicationVersion:  "1.0.0",
		UseMessageDatabase:  false,
		UseFileDatabase:     false,
		UseChatInfoDatabase: false,
		UseTestDataCenter:   false,
		DatabaseDirectory:   "./tdlib-db",
		IgnoreFileNames:     false,
	})

	for {
		currentState, _ := TgClient.Authorize()
		if currentState.GetAuthorizationStateEnum() == tdlib.AuthorizationStateWaitPhoneNumberType {
			fmt.Print("Enter phone: ")
			var number string
			fmt.Scanln(&number)
			_, err := TgClient.SendPhoneNumber(number)
			if err != nil {
				fmt.Printf("Error sending phone number: %v", err)
			}
		} else if currentState.GetAuthorizationStateEnum() == tdlib.AuthorizationStateWaitCodeType {
			fmt.Print("Enter code: ")
			var code string
			fmt.Scanln(&code)
			_, err := TgClient.SendAuthCode(code)
			if err != nil {
				fmt.Printf("Error sending auth code : %v", err)
			}
		} else if currentState.GetAuthorizationStateEnum() == tdlib.AuthorizationStateWaitPasswordType {
			fmt.Print("Enter Password: ")
			var password string
			fmt.Scanln(&password)
			_, err := TgClient.SendAuthPassword(password)
			if err != nil {
				fmt.Printf("Error sending auth password: %v", err)
			}
		} else if currentState.GetAuthorizationStateEnum() == tdlib.AuthorizationStateReadyType {
			fmt.Println("Authorization Ready! Let's rock")
			break
		}
	}

	go VideoUploaderLoop()
}

func VideoUploaderLoop() {
	// load chats to memory otherwise tdlib wouldn't found chat with our bot
	_, err := TgClient.GetChats(9223372036854775807, 0, 10)
	if err != nil {
		log.Panic(err)
	}

	for {
		resp := <-ResponseChan
		m := tdlib.NewInputMessageVideo(tdlib.NewInputFileLocal(resp.fileInfo.Path), nil,
			nil,
			int32(resp.fileInfo.Duration.Seconds()),
			resp.fileInfo.Resolution.Width,
			resp.fileInfo.Resolution.Height,
			true,
			tdlib.NewFormattedText(strconv.FormatInt(resp.ChatID, 10) + ":" + resp.fileInfo.Path, nil),
			0)
		log.Println("send message to bot")
		_, err := TgClient.SendMessage(AgentChatId, 0, false,false,nil, m)
		if err != nil {
			log.Println("failed send message from agent to bot", err)
			continue
		}
	}
}
