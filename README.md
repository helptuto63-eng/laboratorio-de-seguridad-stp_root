# 06 — Ataque STP Root Bridge Takeover

> **Laboratorio de Seguridad en Redes** | Kali Linux + PNETLab | Python + Scapy  
> ⚠️ Uso exclusivo en entornos controlados con fines académicos.

---

## Índice

1. [Objetivo del laboratorio](#1-objetivo-del-laboratorio)
2. [Objetivo del script](#2-objetivo-del-script)
3. [Parámetros del script](#3-parámetros-del-script)
4. [Requisitos](#4-requisitos)
5. [Funcionamiento técnico](#5-funcionamiento-técnico)
6. [Documentación de la red](#6-documentación-de-la-red)
7. [Capturas de pantalla](#7-capturas-de-pantalla)
8. [Contramedidas](#8-contramedidas)

---

## 1. Objetivo del laboratorio

Demostrar el ataque **STP Root Bridge Takeover**, en el cual un atacante manipula el protocolo **STP (Spanning Tree Protocol)** enviando BPDUs (Bridge Protocol Data Units) con la prioridad más alta posible (valor 0) para reclamar el rol de Root Bridge en la red.

STP es un protocolo de capa 2 diseñado para evitar bucles en redes con redundancia. El dispositivo con el Bridge ID más bajo (prioridad + MAC) se convierte en Root Bridge. Al no tener autenticación, cualquier dispositivo puede enviar BPDUs y participar en la elección del Root Bridge.

### Consecuencias del ataque

- El tráfico L2 de toda la red se redirige por el atacante.
- El atacante puede interceptar todas las comunicaciones del segmento.
- Inestabilidad de la red durante la reconvergencia STP.
- Posibles bucles si el atacante falla o se desconecta.

---

## 2. Objetivo del script

El script `06_stp_root_attack.py` envía **Configuration BPDUs** con:

- **Root Priority = 0** (más bajo posible → gana la elección)
- **Root MAC = 00:00:00:00:00:01** (la MAC más baja posible)
- **Path Cost = 0** (ruta directa sin costo)

Enviando estos BPDUs cada 2 segundos (igual que el Hello Timer de STP), el atacante mantiene su posición como Root Bridge mientras el script esté corriendo.

### Resultado del ataque

```
Antes del ataque:
  S1# show spanning-tree vlan 1
  Root ID  Priority  32769
           Address   aa:bb:cc:80:02:00
           This bridge is the root   ← S1 es el Root

Después del ataque:
  S1# show spanning-tree vlan 1
  Root ID  Priority  0
           Address   00:00:00:00:00:01   ← Atacante es el Root
  (ya NO dice "This bridge is the root")
```

---

## 3. Parámetros del script

```bash
sudo python3 06_stp_root_attack.py
```

> Valores hardcodeados en el script:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `IFACE` | `eth0` | Interfaz del atacante |
| `ROOT_MAC` | `00:00:00:00:00:01` | MAC del Root Bridge falso (la más baja) |
| Prioridad Root | `0` | Máxima prioridad STP |
| Hello Timer | `2 segundos` | Igual que STP estándar |

### Control de ejecución

| Acción | Comando |
|--------|---------|
| Iniciar ataque | `sudo python3 06_stp_root_attack.py` |
| Detener ataque | `Ctrl + C` |
| Ver efecto | `python3 06_stp_root_attack.py --effect` |

---

## 4. Requisitos

### Sistema operativo
- Kali Linux 2023 o superior

### Dependencias Python
```bash
pip3 install scapy
```

### Permisos
```bash
sudo python3 06_stp_root_attack.py
```

### Verificación previa en S1
```
S1# show spanning-tree vlan 1
```
Debe mostrar `This bridge is the root` antes de lanzar el ataque.

---

## 5. Funcionamiento técnico

### Estructura del BPDU enviado

```
┌──────────────────────────────────────────────────┐
│  Ethernet 802.3                                   │
│  src: 50:3c:53:00:03:00 (MAC Kali)                │
│  dst: 01:80:c2:00:00:00 (STP multicast)           │
├──────────────────────────────────────────────────┤
│  LLC: dsap=0x42 ssap=0x42 ctrl=0x03              │
├──────────────────────────────────────────────────┤
│  STP Configuration BPDU:                         │
│    Protocol ID  : 0x0000                         │
│    Version      : 0                              │
│    BPDU Type    : 0x00 (Configuration)           │
│    Flags        : 0x00                           │
│    Root ID      : Priority=0 MAC=00:00:00:00:00:01│ ← MÁS BAJO
│    Root Path Cost: 0                             │
│    Bridge ID    : Priority=0 MAC=50:3c:53:00:03:00│
│    Port ID      : 0x8001                         │
│    Message Age  : 0                              │
│    Max Age      : 20s                            │
│    Hello Time   : 2s                             │
│    Forward Delay: 15s                            │
└──────────────────────────────────────────────────┘
```

### Proceso de elección del Root Bridge

```
S1 recibe BPDU del atacante:
  Bridge ID atacante = 0 + 00:00:00:00:00:01
  Bridge ID de S1    = 32769 + aa:bb:cc:80:02:00

  ¿0 < 32769? SÍ → atacante tiene mejor BID → S1 acepta al atacante como Root

S1 actualiza su tabla STP:
  Root Bridge = 00:00:00:00:00:01 (atacante)
  Root Port   = e0/2 (puerto hacia el atacante)
  Todo el tráfico L2 fluye por e0/2 → capturado por el atacante
```

### Flujo de ejecución del script

```
Inicio
  │
  ├─ Obtiene MAC real de eth0
  ├─ Construye BPDU con prioridad 0
  │
  └─ Bucle cada 2 segundos:
       ├─ Envía BPDU por eth0 → destino 01:80:c2:00:00:00
       └─ S1 mantiene al atacante como Root Bridge
```

---

## 6. Documentación de la red

### Topología

```
        ┌─────────────┐
        │   Internet  │
        │    (Net)    │
        └──────┬──────┘
               │
           e0/0│
        ┌──────┴──────┐
        │     R1      │  192.168.10.1
        │   Router    │  MAC: aa:bb:cc:00:01:10
        └──────┬──────┘
           e0/1│
        ┌──────┴──────┐
        │     S1      │  192.168.10.2   ← Root Bridge legítimo
        │   Switch    │  MAC: aa:bb:cc:80:02:00
        │  Priority   │  32769 (default)
        └──┬──────┬───┘
       e0/1│      │e0/2
    ┌──────┴─┐  ┌─┴────────┐
    │  VPC   │  │ Atacante │
    │.10.12  │  │.10.11    │  Root Bridge falso
    └────────┘  └──────────┘  Priority: 0
                               MAC: 00:00:00:00:00:01
```

### Tabla de direccionamiento

| Dispositivo | Interfaz | Dirección IP | Máscara | MAC |
|-------------|----------|-------------|---------|-----|
| R1 | e0/1 | 192.168.10.1 | /24 | aa:bb:cc:00:01:10 |
| S1 | — | 192.168.10.2 | /24 | aa:bb:cc:80:02:00 |
| VPC | eth0 | 192.168.10.12 | /24 | 00:50:79:66:68:04 |
| Atacante | eth0 | 192.168.10.11 | /24 | 50:3c:53:00:03:00 |

### STP antes del ataque

| Parámetro | Valor |
|-----------|-------|
| Root Bridge | S1 |
| Root Priority | 32769 |
| Root MAC | aa:bb:cc:80:02:00 |
| Hello Time | 2s |
| Max Age | 20s |
| Forward Delay | 15s |

---



### 7.1 STP en S1 antes del ataque

```

Comando: S1# show spanning-tree vlan 1
Descripción: S1 es el Root Bridge legítimo. Aparece "This bridge is the root".
```

### 7.2 Ataque en ejecución — Kali

```

Comando: sudo python3 06_stp_root_attack.py
Descripción: BPDUs enviados cada 2 segundos con Root MAC 00:00:00:00:00:01 y prioridad 0.
```

### 7.3 STP en S1 durante el ataque

```

Comando: S1# show spanning-tree vlan 1
Descripción: Root ID muestra Priority 0 y Address 00:00:00:00:00:01. S1 ya no es el Root Bridge.
```

### 7.4 STP en S1 con BPDU Guard activo (contramedida)

```

Comando: S1# show errdisable recovery / show interfaces e0/2 status
Descripción: Puerto e0/2 en err-disabled. S1 recuperó el Root Bridge.
```

---

## 8. Contramedidas

### 8.1 Establecer S1 como Root Bridge permanente

```
S1(config)# spanning-tree vlan 1 root primary
```

### 8.2 Activar PortFast y BPDU Guard en puertos de acceso

```
S1(config)# interface range e0/1 - 2
S1(config-if-range)# spanning-tree portfast
S1(config-if-range)# spanning-tree bpduguard enable
```

### 8.3 Activar Root Guard

```
S1(config)# interface range e0/1 - 2
S1(config-if-range)# spanning-tree guard root
```

### 8.4 Recuperación automática del puerto

```
S1(config)# errdisable recovery cause bpduguard
S1(config)# errdisable recovery interval 60
```

### 8.5 Verificación

```
S1# show spanning-tree vlan 1
S1# show spanning-tree detail
S1# show spanning-tree inconsistentports
S1# show errdisable recovery
S1# show interfaces e0/2 status
```

### 8.6 Resultado esperado

Con BPDU Guard activo, al recibir el primer BPDU del atacante, el puerto e0/2 entra en `err-disabled` inmediatamente. S1 mantiene su rol de Root Bridge y la red permanece estable.

---

## Archivos del repositorio

```
06_stp_root/
├── README.md
├── 06_stp_root_attack.py
└── capturas/
    ├── 01_stp_antes.png
    ├── 02_ataque_kali.png
    ├── 03_stp_durante.png
    └── 04_bpduguard_activo.png
```

---

*Documentación elaborada con fines académicos — Seguridad en Redes*
