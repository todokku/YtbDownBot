package main

import (
	"fmt"
	"github.com/pkg/errors"
	"github.com/rylio/ytdl"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"strings"
)

const MaxFileSizeToUpload = 1500 // Limit size allowed to upload to telegram

func SaveVideo(vid *ytdl.VideoInfo, format720p *ytdl.Format, format360p *ytdl.Format) (*FileInfo, error) {
	// Check file size because it's not allowed upload greater than 1.5 GB
	var format *ytdl.Format
	if format720p != nil {
		format = format720p
	} else {
		format = format360p
	}
	tryAnotherFormat:
	vsize, err := GetYoutubeVideoSize(vid, format)
	if err != nil {
		return nil, errors.WithMessage(err, "failed get youtube video size")
	}
	if vsize > MaxFileSizeToUpload {
		if format == format720p && format360p != nil {
			format = format360p
			goto tryAnotherFormat
		} else {
			return nil, errors.New("file is too big")
		}
	}

	// Download and save file
	fileName := vid.ID + ".mp4"
	var vidFile *os.File
	if vidFile, err = Storage.AddFile(fileName, vsize); err != nil {
		return nil, errors.WithMessage(err, "failed save file")
	}
	defer vidFile.Close()

	err = vid.Download(*format, vidFile)
	if err != nil {
		err = os.Remove("./" + fileName)
		if err != nil {
			log.Error("Failed remove empty file: ", err)
		}
		return nil, err
	}

	res, err := GetVideoResolution(fileName)
	if err != nil {
		return nil, errors.WithMessage(err, "failed get video resolution")
	}

	fileInfo := &FileInfo{fileName, vid.Duration, *res, vsize}

	return fileInfo, nil
}

func GetBestVideoFormats(formats ytdl.FormatList) (*ytdl.Format, *ytdl.Format) {
	// Find best format: 720p or 360p
	var f720p *ytdl.Format
	var f360p *ytdl.Format
	for i := 0; i < len(formats); i++ {
		if formats[i].Itag == 22 {
			f720p = new(ytdl.Format)
			*f720p = formats[i]
		} else if formats[i].Itag == 18 {
			f360p = new(ytdl.Format)
			*f360p = formats[i]
		}
	}

	return f720p, f360p
}

func GetYoutubeVideoSize(vid *ytdl.VideoInfo, format *ytdl.Format) (int64, error) {
	url, err := vid.GetDownloadURL(*format)
	if err != nil {
		return 0, errors.WithMessage(err, "failed get download url")
	}

	return GetFileSizeFromUrl(url.String()), nil
}

func GetFileSizeFromUrl(url string) int64 {
	r, _ := http.Head(url)

	fmt.Printf("File size is %d\n", r.ContentLength / 1048576)

	return r.ContentLength / 1048576
}

func GetVideoResolution(vidPath string) (*Resolution, error) {
	infoCmd := exec.Command("bash", "-c", fmt.Sprintf(`mediainfo '--Inform=Video;%%Width%%\n%%Height%%' '%s'`, vidPath))

	rawRes, err := infoCmd.Output()
	if err != nil {
		return nil, errors.WithMessage(err, "failed execute command to get vid resolution")
	}

	resArr := strings.Split(string(rawRes), "\n")
	w, _ := strconv.Atoi(resArr[0])
	h, _ := strconv.Atoi(resArr[1])

	return &Resolution{int32(w), int32(h)}, nil
}
