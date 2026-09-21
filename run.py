from seed import seed
from fetch import main as run_fetch
from filter import run_filter
from extract import run_extraction
from match import run_matching
from notify import run_notify

if __name__ == "__main__":
    print("=== Seed ===")
    seed()
    print("\n=== Fetch ===")
    run_fetch()
    print("\n=== Filter ===")
    run_filter()
    print("\n=== Extract ===")
    run_extraction()
    print("\n=== Match ===")
    run_matching()
    print("\n=== Notify ===")
    run_notify()
