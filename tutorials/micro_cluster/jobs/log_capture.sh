#!/bin/bash
#ignore this file, use capture.sh to capture jobs
LOG_SRC="/home/slurm/work/micro_cluster/log/jobcomp.log"
LOG_DEST_DIR="/home/slurm/work/micro_cluster/jobs"
LAST_LINE_FILE="/tmp/jobcomp_last_line.txt"  

export TZ="GMT"
mkdir -p "$LOG_DEST_DIR"


if [ ! -f "$LAST_LINE_FILE" ]; then
    echo "0" > "$LAST_LINE_FILE"
fi
LAST_LINE=$(cat "$LAST_LINE_FILE")

while true; do
    sleep 5

    
    if [ ! -f "$LOG_SRC" ]; then
        echo "File $LOG_SRC does not exist, waiting..."
        LAST_LINE=0
        echo "$LAST_LINE" > "$LAST_LINE_FILE"
        continue
    fi

    
    CURRENT_LINES=$(wc -l < "$LOG_SRC" 2>/dev/null || echo 0)


    if [ "$CURRENT_LINES" -gt "$LAST_LINE" ]; then

        NEW_CONTENT=$(tail -n +$((LAST_LINE + 1)) "$LOG_SRC")


        if echo "$NEW_CONTENT" | grep -q "JobId="; then
            TIMESTAMP=$(date +%Y%m%d_%H%M%S)
            DEST_FILE="$LOG_DEST_DIR/jobcomp_${TIMESTAMP}.log"


            echo "$NEW_CONTENT" > "$DEST_FILE"
            echo "Saved new jobs to $DEST_FILE"

            LAST_LINE=$CURRENT_LINES
            echo "$LAST_LINE" > "$LAST_LINE_FILE"
        else
            echo "No new complete job records found, skipping."
        fi
    fi
done