#!/bin/bash
NOWDIR=`pwd`
nohup python $NOWDIR/tianqisvr.py monit > $NOWDIR/monit.log 2>&1 &
 

