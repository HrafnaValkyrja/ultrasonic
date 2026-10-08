#!/usr/bin/env bash
# Keep ~/.claude-shared/board/sessions/ultrasonic.json "updated" fresh every 10 min while the given claude pid lives
# (board README: stale after 30 min). Token-free; heavy_now is still written by the session itself.
pid="$1"; f="$HOME/.claude-shared/board/sessions/ultrasonic.json"
while kill -0 "$pid" 2>/dev/null; do
  python3 -c "import json,datetime,sys;d=json.load(open(sys.argv[1]));d['pid']=int(sys.argv[2]);d['updated']=datetime.datetime.now().astimezone().isoformat(timespec='seconds');json.dump(d,open(sys.argv[1],'w'),indent=1)" "$f" "$pid"
  sleep 600
done
