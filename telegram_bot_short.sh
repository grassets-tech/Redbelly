#!/bin/bash

# Telegram Bot Configuration
# Telegram Bot token - replace with your own bot token
BOT_TOKEN=""

# Telegram Chat ID - replace with your own chat ID
CHAT_ID=""

# Extract the latest block height from local node logs
log_block_height=$(sudo tail -n 1000 /var/log/redbelly/rbn_logs/rbbc_logs.log | grep -a -oP 'number (\d+)'| grep -oP '(\d+)' | tail -n 1)

# Fetch the latest block height from the Redbelly MAINNET RPC endpoint
latest_block_height=$(curl -s https://governors.mainnet.redbelly.network -X POST -H "Content-Type: application/json" \
--data '{"method":"eth_getBlockByNumber","params":["latest",false],"id":1,"jsonrpc":"2.0"}' \
| jq -r '.result.number' | xargs -I {} printf "%d\n" {})

# Calculate the absolute difference between the local and network block height
difference=$(echo "$log_block_height $latest_block_height" | awk '{print ($1 > $2) ? $1 - $2 : $2 - $1}')

# Get current timestamp
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Get system resource usage
cpu_load=$(uptime | awk -F'load average:' '{ print $2 }' | sed 's/^ *//')
ram_used=$(free -m | awk '/Mem:/ {print $3}')
ram_total=$(free -m | awk '/Mem:/ {print $2}')
disk_usage=$(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')

# Determine sync status based on difference
if [ "$difference" -le 1 ]; then
    sync_status="✅ <b>Synced</b>"
else
    sync_status="❌ <b>Not Synced</b>"
fi

# Build HTML message to send to Telegram
html_message="<b>🧾 Node Sync Status (Mainnet)</b>%0A"
html_message+="<b>🕒 Time:</b> $timestamp%0A"
html_message+="<b>📦 Node Block:</b> $log_block_height%0A"
html_message+="<b>🌐 Network Block:</b> $latest_block_height%0A"
html_message+="<b>📉 Difference:</b> $difference blocks%0A"
html_message+="<b>📊 Status:</b> $sync_status%0A"
html_message+="%0A"
html_message+="<b>💻 System Info</b>%0A"
html_message+="<b>🧠 CPU Load:</b> $cpu_load%0A"
html_message+="<b>🗂 RAM:</b> ${ram_used}MB / ${ram_total}MB%0A"
html_message+="<b>💽 Disk:</b> $disk_usage"

# Send the message to Telegram using Bot API
curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
    -d "chat_id=$CHAT_ID" \
    -d "text=$html_message" \
    -d "parse_mode=HTML"
