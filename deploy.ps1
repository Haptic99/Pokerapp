$PiHost = "pi@192.168.8.26"
git add .
git commit -m "Auto-deploy update"
git push
ssh $PiHost 'cd /home/pi/Pokerapp ; git pull ; nohup ./start_poker.sh > /dev/null 2>&1 &'
