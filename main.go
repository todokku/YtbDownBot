package main

import (
	"fmt"
	"net/http"
)

func handler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hi there, I love you!")
}

func main() {
	http.HandleFunc("/", handler)
	go http.ListenAndServe(":80", nil)
	BotMainLoop()
}
