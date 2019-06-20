package main

import (
	"fmt"
	"log"
	"os/exec"
	"sync"
	"time"
)

var ResponseChan chan *Response
var Storage LocalStorage

func init() {
	ResponseChan = make(chan *Response)
}

type Resolution struct {
	Width int32
	Height int32
}

type FileInfo struct {
	Path string
	Duration time.Duration
	Resolution Resolution
	SizeInMB int64
}

type LocalStorage struct {
	Mutex sync.RWMutex
	LocalFiles []*FileInfo
}

func (ls *LocalStorage) RemoveFile(fileName string) {
	ls.Mutex.Lock()
	_, err := exec.Command("bash", "-c", fmt.Sprintf("rm %s", fileName)).Output()
	if err != nil {
		log.Println(err)
	}

	for i := 0; i < len(ls.LocalFiles); i++ {
		if ls.LocalFiles[i].Path == fileName {
			ls.LocalFiles = append(ls.LocalFiles[:i], ls.LocalFiles[i+1:]...)
		}
	}
	ls.Mutex.Unlock()
}

func (ls *LocalStorage) AddFile(info *FileInfo) {
	ls.Mutex.Lock()
	ls.LocalFiles = append(ls.LocalFiles, info)
	ls.Mutex.Unlock()
}
