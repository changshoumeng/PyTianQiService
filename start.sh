#!/bin/bash
NOWDIR=`pwd`
rm -rf log/*
rm -rf run/*
nohup python $NOWDIR/tianqisvr.py > $NOWDIR/log/unhandle_error.log 2>&1 &

