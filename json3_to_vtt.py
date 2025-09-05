#!/usr/bin/env python3
"""
Convertitore da JSON3 (sottotitoli YouTube) a WebVTT

Questo script converte i file di sottotitoli YouTube dal formato JSON3
al formato WebVTT (.vtt), mantenendo la sincronizzazione temporale
e pulendo il testo dai caratteri indesiderati.

Autore: Francesco
Versione: 1.0
"""

import json
import argparse
import sys
import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Any


class JSON3ToVTTConverter:
    """
    Convertitore da formato JSON3 (YouTube) a WebVTT.
    
    Gestisce il parsing dei file JSON3 di YouTube e la conversione
    in formato WebVTT standard, con pulizia del testo e validazione.
    """
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Inizializza il convertitore.
        
        Args:
            log_level: Livello di logging (default: INFO)
        """
        self.setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        
    def setup_logging(self, level: int) -> None:
        """
        Configura il sistema di logging.
        
        Args:
            level: Livello di logging
        """
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def validate_json3_structure(self, data: Dict[str, Any]) -> bool:
        """
        Valida che il file JSON abbia la struttura corretta per JSON3.
        
        Args:
            data: Dati JSON caricati
            
        Returns:
            True se la struttura è valida, False altrimenti
        """
        if not isinstance(data, dict):
            self.logger.error("Il file JSON non contiene un oggetto alla radice")
            return False
            
        if 'events' not in data:
            self.logger.error("Manca il campo 'events' nel JSON3")
            return False
            
        if not isinstance(data['events'], list):
            self.logger.error("Il campo 'events' deve essere un array")
            return False
            
        # Verifica che almeno alcuni eventi abbiano la struttura corretta
        valid_events = 0
        for event in data['events'][:5]:  # Controlla i primi 5 eventi
            if isinstance(event, dict) and 'tStartMs' in event:
                valid_events += 1
                
        if valid_events == 0:
            self.logger.error("Nessun evento valido trovato con 'tStartMs'")
            return False
            
        self.logger.info(f"File JSON3 validato: {len(data['events'])} eventi trovati")
        return True
    
    def milliseconds_to_vtt_time(self, milliseconds: int) -> str:
        """
        Converte millisecondi nel formato timestamp WebVTT.
        
        Args:
            milliseconds: Timestamp in millisecondi
            
        Returns:
            Stringa nel formato HH:MM:SS.mmm
        """
        if milliseconds < 0:
            milliseconds = 0
            
        total_seconds = milliseconds // 1000
        ms = milliseconds % 1000
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"
    
    def clean_text(self, text: str) -> str:
        """
        Pulisce il testo dei sottotitoli da caratteri indesiderati.
        
        Args:
            text: Testo grezzo
            
        Returns:
            Testo pulito
        """
        if not text:
            return ""
            
        # Rimuovi tag HTML comuni
        text = re.sub(r'<[^>]+>', '', text)
        
        # Rimuovi newline multipli e spazi eccessivi
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Rimuovi spazi all'inizio e alla fine
        text = text.strip()
        
        # Gestisci caratteri speciali comuni nei sottotitoli YouTube
        replacements = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '\u00a0': ' ',  # Non-breaking space
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        return text
    
    def extract_text_from_segments(self, segments: List[Dict[str, Any]]) -> str:
        """
        Estrae il testo dai segmenti di un evento JSON3.
        
        Args:
            segments: Lista dei segmenti dell'evento
            
        Returns:
            Testo combinato e pulito
        """
        if not segments:
            return ""
            
        text_parts = []
        for segment in segments:
            if isinstance(segment, dict):
                # Prova diversi campi per il testo
                text = segment.get('utf8', '') or segment.get('text', '')
                if text:
                    text_parts.append(str(text))
                    
        combined_text = ''.join(text_parts)
        return self.clean_text(combined_text)
    
    def parse_json3_events(self, data: Dict[str, Any]) -> List[Tuple[int, int, str]]:
        """
        Estrae gli eventi di sottotitoli dal JSON3.
        
        Args:
            data: Dati JSON3 caricati
            
        Returns:
            Lista di tuple (start_ms, end_ms, text)
        """
        events = []
        
        for event in data.get('events', []):
            if not isinstance(event, dict):
                continue
                
            start_ms = event.get('tStartMs')
            duration_ms = event.get('dDurationMs')
            segments = event.get('segs', [])
            
            # Verifica che abbiamo i dati necessari
            if start_ms is None:
                continue
                
            # Calcola il tempo di fine
            if duration_ms is not None:
                end_ms = start_ms + duration_ms
            else:
                # Se non c'è durata, usa una durata di default di 2 secondi
                end_ms = start_ms + 2000
                
            # Estrai il testo
            text = self.extract_text_from_segments(segments)
            
            # Salta eventi senza testo significativo
            if not text or len(text.strip()) < 1:
                continue
                
            events.append((int(start_ms), int(end_ms), text))
            
        # Ordina per timestamp di inizio
        events.sort(key=lambda x: x[0])
        
        self.logger.info(f"Estratti {len(events)} eventi validi con testo")
        return events
    
    def merge_overlapping_events(self, events: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
        """
        Unisce eventi sovrapposti o consecutivi con testo simile.
        
        Args:
            events: Lista di eventi (start_ms, end_ms, text)
            
        Returns:
            Lista di eventi ottimizzata
        """
        if not events:
            return []
            
        merged = []
        current_start, current_end, current_text = events[0]
        
        for start, end, text in events[1:]:
            # Se l'evento corrente si sovrappone o è molto vicino al precedente
            # e il testo è simile, uniscili
            if (start <= current_end + 500 and  # 500ms di tolleranza
                text.strip().lower() == current_text.strip().lower()):
                # Estendi il tempo di fine
                current_end = max(current_end, end)
            else:
                # Aggiungi l'evento precedente e inizia uno nuovo
                merged.append((current_start, current_end, current_text))
                current_start, current_end, current_text = start, end, text
                
        # Aggiungi l'ultimo evento
        merged.append((current_start, current_end, current_text))
        
        if len(merged) != len(events):
            self.logger.info(f"Uniti {len(events) - len(merged)} eventi sovrapposti")
            
        return merged
    
    def generate_vtt_content(self, events: List[Tuple[int, int, str]]) -> str:
        """
        Genera il contenuto del file WebVTT.
        
        Args:
            events: Lista di eventi (start_ms, end_ms, text)
            
        Returns:
            Contenuto VTT completo
        """
        lines = ["WEBVTT", ""]
        
        for i, (start_ms, end_ms, text) in enumerate(events, 1):
            start_time = self.milliseconds_to_vtt_time(start_ms)
            end_time = self.milliseconds_to_vtt_time(end_ms)
            
            # Aggiungi numero della caption (opzionale ma utile)
            lines.append(f"{i}")
            lines.append(f"{start_time} --> {end_time}")
            lines.append(text)
            lines.append("")  # Riga vuota tra le caption
            
        return "\n".join(lines)
    
    def convert_file(self, input_path: str, output_path: str) -> bool:
        """
        Converte un file JSON3 in WebVTT.
        
        Args:
            input_path: Percorso del file JSON3 di input
            output_path: Percorso del file VTT di output
            
        Returns:
            True se la conversione è riuscita, False altrimenti
        """
        try:
            # Verifica che il file di input esista
            if not os.path.exists(input_path):
                self.logger.error(f"File di input non trovato: {input_path}")
                return False
                
            self.logger.info(f"Inizio conversione: {input_path} -> {output_path}")
            
            # Carica il file JSON3
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Valida la struttura
            if not self.validate_json3_structure(data):
                return False
                
            # Estrai gli eventi
            events = self.parse_json3_events(data)
            
            if not events:
                self.logger.error("Nessun evento valido trovato nel file JSON3")
                return False
                
            # Ottimizza gli eventi
            events = self.merge_overlapping_events(events)
            
            # Genera il contenuto VTT
            vtt_content = self.generate_vtt_content(events)
            
            # Scrivi il file di output
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(vtt_content)
                
            self.logger.info(f"Conversione completata: {len(events)} sottotitoli salvati")
            return True
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Errore nel parsing JSON: {e}")
            return False
        except IOError as e:
            self.logger.error(f"Errore I/O: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Errore imprevisto: {e}")
            return False


def main():
    """
    Funzione principale per l'uso da linea di comando.
    """
    parser = argparse.ArgumentParser(
        description='Converte file JSON3 (sottotitoli YouTube) in formato WebVTT',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  %(prog)s input.json3 -o output.vtt
  %(prog)s sottotitoli.json3 --output sottotitoli.vtt --verbose
  %(prog)s video.json3  # Salva come video.vtt
        """
    )
    
    parser.add_argument(
        'input_file',
        help='File JSON3 di input da convertire'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='File VTT di output (default: stesso nome con estensione .vtt)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Output verboso con informazioni dettagliate'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Modalità silenziosa (solo errori)'
    )
    
    args = parser.parse_args()
    
    # Determina il livello di logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
        
    # Determina il file di output
    if args.output:
        output_file = args.output
    else:
        # Cambia l'estensione da .json3 a .vtt
        base_name = os.path.splitext(args.input_file)[0]
        output_file = f"{base_name}.vtt"
        
    # Crea il convertitore ed esegui la conversione
    converter = JSON3ToVTTConverter(log_level)
    
    success = converter.convert_file(args.input_file, output_file)
    
    if success:
        print(f"✓ Conversione completata: {output_file}")
        sys.exit(0)
    else:
        print("✗ Conversione fallita")
        sys.exit(1)


if __name__ == "__main__":
    main()
