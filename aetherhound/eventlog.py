import csv, json, os, datetime
FIELDS = ["time", "duration_s", "freq_hz", "peak_score", "decoded_text", "morse", "bits", "keying_unit_s"]
class EventLog:
    def __init__(self, d):
        os.makedirs(d, exist_ok=True)
        self.jsonl = os.path.join(d, "events.jsonl"); self.csvp = os.path.join(d, "events.csv")
    def write(self, ev):
        row = {"time": datetime.datetime.fromtimestamp(ev["start_ts"]).isoformat(timespec="milliseconds")}
        row.update({k: ev[k] for k in FIELDS[1:]})
        with open(self.jsonl, "a") as f: f.write(json.dumps(row) + "\n")
        new = not os.path.exists(self.csvp)
        with open(self.csvp, "a", newline="") as f:
            w = csv.DictWriter(f, FIELDS)
            if new: w.writeheader()
            w.writerow(row)
        return row
