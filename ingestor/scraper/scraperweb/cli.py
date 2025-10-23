import argparse
from pathlib import Path

from logging_json import log_json
from rss import fetch_and_parse_all
from sink import write_to_sink


def main():
    parser = argparse.ArgumentParser(description="Fetch crypto RSS and write NDJSON")
    parser.add_argument("--base-dir", default=".", help="Base directory to write data under (default: .)")
    args = parser.parse_args()

    try:
        items = fetch_and_parse_all()
        written, out_file = write_to_sink(args.base_dir, items)
        log_json(
            "info",
            "rss_run_completed",
            written_count=written,
            output=str(Path(out_file)),
            sources=["coindesk", "cointelegraph"],
        )
    except Exception as e:
        log_json("error", "rss_run_failed", error=str(e))
        raise


if __name__ == "__main__":
    main()


