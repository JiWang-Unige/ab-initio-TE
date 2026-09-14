import glob
import json
import re

LOG_PATTERNS = {
    "A1 (Frozen)": "logs/exp008_A1_frozen_*.out",
    "A2 (Cold Frozen)": "logs/exp004_A2_*.out",
    "B1 (Warm Trainable)": "logs/exp004_B1_*.out",
    "B2 (Warm Frozen)": "logs/exp004_B2_*.out",
    "K-mer": "logs/exp007_kmer_*.out",
    "Variable Length": "logs/exp005v2_varlen_*.out"
}

def extract_metrics(log_file):
    try:
        with open(log_file, "r") as f:
            content = f.read()
            # Look for JSON block at end
            match = re.search(r"Test Results:\s*(\{.*\})", content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return data.get("5_class", {})
    except Exception as e:
        return None
    return None

print(f"{'Model':<20} | ARI    | NMI    | Purity")
print("-" * 50)

for name, pattern in LOG_PATTERNS.items():
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"{name:<20} | N/A    | N/A    | N/A")
        continue
    
    # Use latest log file
    latest_log = files[-1]
    metrics = extract_metrics(latest_log)
    
    if metrics:
        ari = metrics.get("ari", 0)
        nmi = metrics.get("nmi", 0)
        purity = metrics.get("purity", 0)
        print(f"{name:<20} | {ari:.4f} | {nmi:.4f} | {purity:.4f}")
    else:
        print(f"{name:<20} | Failed | Failed | Failed")
