"""Forensic Incident Report Generator (Week 4 Polish Deliverable).
Parses events.jsonl / events.csv and generates comprehensive terminal reports
and standalone HTML forensic dashboards.
"""
import argparse, json, os, sys
import datetime

def generate_report(event_log_path, html_output=None):
    if not os.path.exists(event_log_path):
        print(f"[!] Log file not found: {event_log_path}")
        return
        
    events = []
    with open(event_log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
                    
    print("\n" + "=" * 80)
    print(" AETHERHOUND FORENSIC SIGINT INCIDENT REPORT")
    print("=" * 80)
    print(f"  Log File Source : {event_log_path}")
    print(f"  Total Incidents : {len(events)}")
    print(f"  Report Time     : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    if not events:
        print("  [!] No covert channel incidents recorded yet.")
        print("=" * 80 + "\n")
        return
        
    # Group by carrier frequency
    bands = {}
    for ev in events:
        carrier = round(ev["freq_hz"] / 250) * 250
        bands.setdefault(carrier, []).append(ev)
        
    print("\n[+] INCIDENTS BY FREQUENCY CARRIER:")
    for freq, ev_list in sorted(bands.items()):
        total_time = sum(e["duration_s"] for e in ev_list)
        print(f"  Carrier ~{freq:>8.1f} Hz : {len(ev_list)} incident(s), total duration {total_time:.2f}s")
        
    print("\n[+] DETAILED INCIDENT CHRONOLOGY:")
    print(f"  {'TIMESTAMP':<24} {'CARRIER (Hz)':<14} {'DUR (s)':<8} {'PEAK Z':<8} {'DECODED PAYLOAD'}")
    print("  " + "-" * 76)
    for ev in events:
        ts = ev.get("time", "N/A")
        f_hz = f"{ev.get('freq_hz', 0.0):.1f}"
        dur = f"{ev.get('duration_s', 0.0):.2f}"
        score = f"{ev.get('peak_score', 0.0):.1f}"
        msg = ev.get("decoded_text", "")
        print(f"  {ts:<24} {f_hz:<14} {dur:<8} {score:<8} '{msg}'")
    print("=" * 80 + "\n")
    
    if html_output:
        _write_html_report(events, html_output)

def _write_html_report(events, out_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    rows_html = []
    for ev in events:
        rows_html.append(f"""
        <tr>
            <td><code>{ev.get('time')}</code></td>
            <td><strong>{ev.get('freq_hz', 0.0):.1f} Hz</strong></td>
            <td>{ev.get('duration_s', 0.0):.2f}s</td>
            <td><span class="badge score">{ev.get('peak_score', 0.0):.1f}</span></td>
            <td><code>{ev.get('morse', '')}</code></td>
            <td class="payload"><strong>{ev.get('decoded_text', '')}</strong></td>
        </tr>
        """)
        
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AetherHound Forensic Covert Channel Report</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; background: #0d1117; color: #c9d1d9; padding: 24px; }}
    h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 12px; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 18px; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ text-align: left; padding: 10px 14px; border-bottom: 1px solid #21262d; }}
    th {{ background: #21262d; color: #8b949e; text-transform: uppercase; font-size: 12px; }}
    tr:hover {{ background: #1c2128; }}
    .badge {{ background: #f85149; color: #fff; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 11px; }}
    .payload {{ color: #7ee787; font-size: 14px; }}
</style>
</head>
<body>
    <h1>AetherHound Forensic Security Report</h1>
    <div class="card">
        <h3>Air-Gapped Covert Channel Incident Summary</h3>
        <p><strong>Total Detected Exfiltrations:</strong> {len(events)}</p>
        <p><strong>Generated At:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    <div class="card">
        <h3>Detected Exfiltration Incident Log</h3>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Carrier Frequency</th>
                    <th>Duration</th>
                    <th>Peak Anomaly Score</th>
                    <th>Morse Demodulation</th>
                    <th>Decoded Exfiltrated Text</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[+] Forensic HTML Dashboard saved to: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate AetherHound Forensic Incident Report")
    parser.add_argument("--file", "-f", default="logs/events.jsonl", help="Path to events.jsonl")
    parser.add_argument("--html", help="Path to export HTML report (e.g. logs/report.html)")
    args = parser.parse_args()
    generate_report(args.file, args.html)

if __name__ == "__main__":
    main()
