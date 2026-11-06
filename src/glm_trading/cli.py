"""Command-line entry point."""

import argparse

from .config import load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--config", default="config/example.yml")
    args = parser.parse_args()
    config = load_config(args.config)
    print(f"Configuration valid: {config.ticker}, evaluation {config.evaluation_start}–{config.evaluation_end}")


if __name__ == "__main__":
    main()
