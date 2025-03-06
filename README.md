# Video-Editor
pyton script for compressing and joining video files, essentially UI for few ffmpeg tools

It will not work if you don't have ffmpeg installed!

Most ffmpeg settings are hard coded and few are user selection. Processing will get videos down to the selected ratio, aac 128k
Normal h.264 video format, fast/medium/slow.. -ffmpeg setting and crf slider recommended 17-30 slider bar

As far as I'm concerned haven't added any libraries that aren't readily available

ffmpeg is called by sub process with cmd syntax

