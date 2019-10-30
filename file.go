package main

import (
	"fmt"
	"github.com/c2h5oh/datasize"
	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"time"
)

var ResponseChan chan *Response
var Storage LocalStorage

func init() {
	Storage.FreeSpaceCond = sync.NewCond(&Storage)
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
	Size datasize.ByteSize
	ThumbnailURL string
}

type LocalStorage struct {
	sync.Mutex
	LocalFiles    []string
	FreeSpaceCond *sync.Cond
}

func (ls *LocalStorage) RemoveFile(fileName string) {
	ls.Mutex.Lock()
	defer ls.Mutex.Unlock()

	fileName = "./" + fileName

	err := os.Remove(fileName)
	if err != nil {
		log.Error(err)
	}
	// notify all goroutines that waiting for free space
	ls.FreeSpaceCond.Broadcast()

	// remove from LocalFiles
	for i := 0; i < len(ls.LocalFiles); i++ {
		if ls.LocalFiles[i] == fileName {
			ls.LocalFiles = append(ls.LocalFiles[:i], ls.LocalFiles[i+1:]...)
		}
	}
}

func (ls *LocalStorage) AddFile(fileName string, size datasize.ByteSize) (*os.File, error) {
	ls.Mutex.Lock()
	defer ls.Mutex.Unlock()

	for {
		dspace, err := getFreeSpace()
		if err != nil {
			return nil, errors.WithMessage(err, "Failed get amount of free space")
		}
		if dspace < size {
			// wait for free space
			log.WithField("filename", fileName).Info("Waiting for free space...")
			ls.FreeSpaceCond.Wait()
		} else {
			break
		}
	}

	if err := fallocate("./" + fileName, size); err != nil {
		return nil, errors.WithMessage(err, "pre allocate disk space failed")
	}
	vidFile, err := os.OpenFile("./" + fileName, os.O_CREATE|os.O_WRONLY, os.ModePerm)
	if err != nil {
		return nil, errors.WithMessage(err, "failed open file for video saving")
	}
	ls.LocalFiles = append(ls.LocalFiles, vidFile.Name())

	return vidFile, nil
}

// return free disk space in MB
func getFreeSpace() (datasize.ByteSize, error) {
	dfCmd := exec.Command("bash", "-c", fmt.Sprintf(`df -k $(pwd) | awk '{ print $4 }' | tail -n1`))
	cmdOut, err := dfCmd.Output()
	if err != nil {
		return 0, errors.WithMessage(err, "cmd failed")
	}

	cmdOutStr := string(cmdOut)
	cmdOutStr = strings.ReplaceAll(cmdOutStr,"\n", "")
	size, err := strconv.ParseUint(cmdOutStr, 10, 64)
	if err != nil {
		fmt.Println(err)
	}

	return datasize.ByteSize(size*1024), nil
}

// preallocate file
func fallocate(file string, size datasize.ByteSize) error {
	dfCmd := exec.Command("bash", "-c", fmt.Sprintf(`fallocate -l %d %s`, size.Bytes(), file))
	_, err := dfCmd.Output()
	if err != nil {
		return errors.WithMessage(err, "cmd failed")
	}

	return nil
}