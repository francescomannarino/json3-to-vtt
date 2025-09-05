# Convertitore JSON3 to WebVTT

Script Python per convertire i sottotitoli YouTube dal formato JSON3 al formato WebVTT (.vtt).

## Caratteristiche

- ✅ Parsing robusto dei file JSON3 di YouTube
- ✅ Conversione precisa dei timestamp da millisecondi a formato WebVTT
- ✅ Pulizia automatica del testo (rimozione HTML, caratteri speciali, etc.)
- ✅ Gestione completa degli errori e logging dettagliato
- ✅ Interfaccia da linea di comando intuitiva
- ✅ Supporto per caratteri Unicode ed emoji
- ✅ Unione automatica di eventi sovrapposti
- ✅ Validazione della struttura JSON3

## Installazione

Non sono richieste dipendenze esterne. Lo script usa solo librerie Python standard.

```bash
# Clona o scarica lo script
chmod +x json3_to_vtt.py
```

## Utilizzo

### Linea di comando

```bash
# Conversione semplice
python json3_to_vtt.py input.json3

# Specificare file di output
python json3_to_vtt.py input.json3 -o output.vtt

# Modalità verbosa
python json3_to_vtt.py input.json3 --verbose

# Modalità silenziosa (solo errori)
python json3_to_vtt.py input.json3 --quiet
```

### Come modulo Python

```python
from json3_to_vtt import JSON3ToVTTConverter

converter = JSON3ToVTTConverter()
success = converter.convert_file('input.json3', 'output.vtt')
```

## Formato JSON3

Il formato JSON3 è utilizzato da YouTube per i sottotitoli automatici. Struttura tipica:

```json
{
  "events": [
    {
      "tStartMs": 0,
      "dDurationMs": 3000,
      "segs": [
        {
          "utf8": "Testo del sottotitolo"
        }
      ]
    }
  ]
}
```

## Formato WebVTT Output

```
WEBVTT

1
00:00:00.000 --> 00:00:03.000
Testo del sottotitolo

2
00:00:03.500 --> 00:00:07.700
Altro sottotitolo
```

## Gestione Errori

Lo script gestisce automaticamente:

- File JSON malformati o corrotti
- Eventi senza timestamp o testo
- Caratteri speciali e encoding UTF-8
- Eventi sovrapposti o fuori sequenza
- File di input inesistenti

## Logging

Tre livelli di logging disponibili:

- **Normal**: Informazioni di base sulla conversione
- **Verbose** (`-v`): Dettagli completi del processo
- **Quiet** (`--quiet`): Solo messaggi di errore

## Requisiti

- Python 3.6+
- Solo librerie standard Python (json, argparse, sys, os, re, logging)

## Licenza

Questo script è fornito "as-is" per uso educativo e personale.
