import sys
from pathlib import Path

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.indexer import PolicyIndexBuilder

def main():
    print("=" * 60)
    print("Enterprise Policy RAG Assistant: Ingestion & Indexing Pipeline")
    print("=" * 60)
    builder = PolicyIndexBuilder()
    stats = builder.build_indexes()
    print("\nIngestion Summary:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("=" * 60)

if __name__ == "__main__":
    main()
