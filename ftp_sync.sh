#!/bin/bash

HOST="192.168.88.253"
USER="blackhat"
PASS="heregoesnothing"
#HOST="192.168.4.1"
#USER="micro"
#PASS="python"
FTPURL="ftp://$USER:$PASS@$HOST"
LCD="."
RCD="/flash/"
#DELETE="--delete"

lftp -vvv -c "set ftp:list-options -a;
set mirror:set-permissions false;
set ftp:list-empty-ok true;
open '$FTPURL';
lcd $LCD;
cd $RCD;
mirror --reverse \
	$DELETE \
	--verbose \
	--exclude-glob MicroWebSrv/* \
	--exclude-glob Makefile \
	--exclude-glob *.pyc \
	--exclude-glob *.sw* \
	--exclude-glob ftp_sync.sh"
