import argparse
from datetime import datetime, timezone, timedelta
import requests
import time
from dateutil import parser
from decimal import Decimal

ether_in_wei = Decimal("1000000000000000000")
blockChanges: list[tuple[int, datetime]] = []

def clear_screen():
    print("\033[2J\033[H", end='', flush=True)

def get_block_ps(blockChange: list[tuple[int, datetime]]) -> float:
    (startBlock, startTime) = blockChange[0]
    (endBlock, endTime) = blockChange[-1]
    timeChange = endTime.replace(tzinfo=timezone.utc) - startTime.replace(tzinfo=timezone.utc)
    if timeChange.total_seconds() == 0:
        return 0
    return float(endBlock - startBlock) / timeChange.total_seconds()

def run_loop(address: str, min_addresss_bal: int, refresh_seconds: int):
    try:
        while True:
            result = monitor(address, min_addresss_bal)
            clear_screen()
            print(result)
            time.sleep(refresh_seconds)
    except KeyboardInterrupt:
        print("\nExiting")
    except BaseException as e:
        print(f"\nGot error when connecting to {address}, be sure status server is enabled in SEVM with flags --statusserver.addr=127.0.0.1 --statusserver.port=6539")
    print(e)
    exit(1)

def monitor(address: str, min_addresss_bal: int) -> str:
    url = address + "/status"
    parts = []
    parts.append(f"Monitoring url {url}")
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()
    isRecoveryComplete = bool(data["isRecoveryComplete"])
    lastCommittedBlockAt = datetime.fromtimestamp(0) if data["lastCommittedBlockAt"] == "" else parser.parse(data["lastCommittedBlockAt"])
    timeSinceLastBlock = datetime.now(timezone.utc)-lastCommittedBlockAt.replace(tzinfo=timezone.utc)
    currentBlock = int(data["currentBlock"])
    lastBlockFromGovernors = int(data["lastBlockFromGovernors"])
    lastSyncedWithGovernorNodes = datetime.fromtimestamp(0) if data["lastSyncedWithGovernorNodes"] == "" else parser.parse(data["lastSyncedWithGovernorNodes"])
    timeSinceLastSyncWithGovs = datetime.now(timezone.utc)-lastSyncedWithGovernorNodes.replace(tzinfo=timezone.utc)
    blocksBehind = lastBlockFromGovernors - currentBlock
    blockChanges.append((currentBlock, lastCommittedBlockAt))
    if len(blockChanges) > 10:
        blockChanges.pop(0)
    currentSuperblock = int(data["currentSuperblock"])
    lastSyncedWithBootnodes = datetime.fromtimestamp(0) if data["lastSyncedWithBootnodes"] == "" else parser.parse(data["lastSyncedWithBootnodes"])
    lastSuperblockFromBootnodes = int(data["lastSuperblockFromBootnodes"])
    timeSinceLastSyncWithBootnodes = datetime.now(timezone.utc)-lastSyncedWithBootnodes.replace(tzinfo=timezone.utc)
    superblocksBehind = lastSuperblockFromBootnodes - currentSuperblock
    certificateDnsNames: list[str] = data["certificateDnsNames"]
    certificatesValidUpto = datetime.fromtimestamp(0) if data["certificatesValidUpto"] == "" else parser.parse(data["certificatesValidUpto"])
    certificateValidDuration = certificatesValidUpto.replace(tzinfo=timezone.utc)-datetime.now(timezone.utc)
    signingAddress = str(data["signingAddress"])
    signingAddressBalance = Decimal(data["signingAddressBalance"]) / ether_in_wei
    version = str(data["version"])
    
    parts.append("\nSync Status:")
    if isRecoveryComplete:
        parts.append("Node has completed initial sync")
    else:
        parts.append("Node is still running inital sync")

    parts.append("\nBlock Information:")
    parts.append(f"Current block: {currentBlock}")
    parts.append(f"Block processed at {lastCommittedBlockAt.astimezone()}, i.e. {timeSinceLastBlock} ago")
    
    if timeSinceLastBlock > timedelta(minutes=5):
        parts.append(f"\033[31mWARNING\033[0m: node has not processed a block in more than 5 minutes, may be out of sync with network")
    
    parts.append(f"Block process rate: {get_block_ps(blockChanges)} blocks per second")
    if blocksBehind > 100:
        parts.append(f"\033[31mWARNING\033[0m: node is {blocksBehind} blocks behind the governor")
    
    parts.append(f"Last block seen from governors: {lastBlockFromGovernors}")
    parts.append(f"Time of last block sync with governors: {lastSyncedWithGovernorNodes.astimezone()}, i.e. {timeSinceLastSyncWithGovs} ago")

    if timeSinceLastSyncWithGovs > timedelta(minutes=1):
        parts.append(f"\033[31mWARNING\033[0m: node has not synced block number with governors in more than 1 minute, node may be out of sync with network")

    parts.append("\nSuperblock Information:")
    parts.append(f"Current superblock: {currentSuperblock}")
    if superblocksBehind > 100:
        parts.append(f"\033[31mWARNING\033[0m: node is {superblocksBehind} superblocks behind the bootnodes")


    parts.append(f"Last superblock seen from bootnodes: {lastSuperblockFromBootnodes}")
    parts.append(f"Time of last superblock sync with bootnodes: {lastSyncedWithBootnodes.astimezone()}, i.e. {timeSinceLastSyncWithBootnodes} ago")
    
    if timeSinceLastSyncWithGovs > timedelta(minutes=2):
        parts.append(f"\033[31mWARNING\033[0m: node has not synced superblock number with bootnodes in more than 2 minutes, node may be out of sync with network")

    parts.append(f"\nSigning address information:")
    parts.append(f"Address {signingAddress} \nBalance: {signingAddressBalance} RBNT")

    if min_addresss_bal > signingAddressBalance:
        parts.append(f"\033[31mWARNING\033[0m: signing address balance is less than the minimum needed of {min_addresss_bal} RBNT")

    parts.append(f"\nCertificate information:")
    parts.append(f"Certificate DNS names: {certificateDnsNames}")
    parts.append(f"Certificate valid until {certificatesValidUpto.astimezone()}, i.e. {certificateValidDuration}")
    
    if certificateValidDuration <= timedelta():
        parts.append(f"\033[31mWARNING\033[0m: Certificate has expired")

    if certificateValidDuration <= timedelta(days=7):
        parts.append(f"\033[31mWARNING\033[0m: Certificate will expire soon")

    parts.append(f"\nBinary version: {version}")
    return "\n".join(parts)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch the stats of a local Redbelly node")
    parser.add_argument("-a", "--address", type=str, default="http://localhost:6539", help="Address of the Redbelly node's status server")
    parser.add_argument("-mb", "--minBalance", type=int, default=10, help="Minimum signing address balance in RBNT before warning")
    parser.add_argument("-r", "--refreshSeconds", type=int, default=5, help="Frequency to refresh values")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    run_loop(args.address, args.minBalance, args.refreshSeconds)

