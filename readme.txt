I did a small script in python it is very very ugly but at least it
works. Feel free to improve it...  I then added a konqueror service menu
to resize & upload in
.kde/share/apps/konqueror/servicemenus/imageuploader.desktop:
 
 [Desktop Entry]
 ServiceTypes=image/*
 Actions=upsmall;upmedium;uplarge;uporig
 X-KDE-Submenu=Upload
 TryExec=convert
 
 [Desktop Action upsmall]
 Name=Small (640xYYY)
 Icon=image
 Exec=/home/bilibao/upload-picasa.py -r 640 %F
 
 [Desktop Action upmedium]
 Name=Medium (1024xYYY)
 Icon=image
 Exec=/home/bilibao/upload-picasa.py -r 1024 %F > /tmp/logupload
 
 [Desktop Action uplarge]
 Name=Large (1280xYYY)
 Icon=image
 Exec=/home/bilibao/upload-picasa.py -r 1280 %F
 
 [Desktop Action uporig]
 Name=Original
 Icon=image
 Exec=/home/bilibao/upload.py %F
