"""Xem lại các session typing đã ghi.

Chạy:        python typing_viewer.py             (chọn từ danh sách)
Hoặc:        python typing_viewer.py <số>        (xem session theo index)
Hoặc:        python typing_viewer.py latest      (xem session mới nhất)
"""
import sys
from collections import Counter
from pathlib import Path

LOG_DIR = Path(__file__).parent / "typing_logs"


def list_sessions():
    return sorted(LOG_DIR.glob("typing_*.log"))


def reconstruct(log_path: Path):
    chars = []
    counter: Counter = Counter()
    total = 0
    first_ts = None
    last_ts = None

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t", 1)
            if len(parts) != 2:
                continue
            ts, key = parts
            if first_ts is None:
                first_ts = ts
            last_ts = ts
            counter[key] += 1
            total += 1

            if key == "<space>":
                chars.append(" ")
            elif key == "<enter>":
                chars.append("\n")
            elif key == "<tab>":
                chars.append("\t")
            elif key == "<backspace>":
                if chars:
                    chars.pop()
            elif key.startswith("<"):
                continue
            else:
                chars.append(key)

    return {
        "first_ts": first_ts,
        "last_ts": last_ts,
        "total": total,
        "counter": counter,
        "text": "".join(chars),
    }


def show(log_path: Path):
    info = reconstruct(log_path)
    print(f"\n=== {log_path.name} ===")
    print(f"Bắt đầu : {info['first_ts']}")
    print(f"Kết thúc: {info['last_ts']}")
    print(f"Tổng phím: {info['total']}")

    print("\n--- Top 15 phím ---")
    for k, c in info["counter"].most_common(15):
        label = repr(k) if not k.startswith("<") else k
        print(f"  {label:<15} {c}")

    print("\n--- Nội dung tái tạo (sau khi xử lý backspace/space/enter) ---")
    print(info["text"])
    print("\n=== Hết ===\n")


def main():
    sessions = list_sessions()
    if not sessions:
        print(f"Chưa có log nào trong {LOG_DIR}")
        return

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg == "latest":
        show(sessions[-1])
        return
    if arg is not None and arg.isdigit():
        idx = int(arg)
        if 0 <= idx < len(sessions):
            show(sessions[idx])
            return
        print(f"Index không hợp lệ. Có {len(sessions)} session.")
        return

    print("Các session đã ghi:")
    for i, s in enumerate(sessions):
        print(f"  [{i}] {s.name}")
    choice = input("\nChọn số (Enter = mới nhất): ").strip()
    idx = int(choice) if choice else len(sessions) - 1
    show(sessions[idx])


if __name__ == "__main__":
    main()
