"""Command-line entry point."""

import argparse
import json

import requests

from .config import load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "download", "run", "replay", "evaluate", "report"])
    parser.add_argument("--config", default="config/example.yml")
    parser.add_argument("--period", choices=["development", "evaluation"], default="evaluation")
    args = parser.parse_args()
    config = load_config(args.config)
    try:
        if args.command == "check":
            print(f"Configuration valid: {config.ticker}, evaluation {config.evaluation_start}–{config.evaluation_end}")
        elif args.command == "download":
            from .ingestion import download
            bars, sources = download(config)
            print(f"Saved {bars} price rows and {sources} earnings releases")
        elif args.command in {"run", "replay"}:
            from .evaluation import save_run
            from .llm import Ollama
            replay = args.command == "replay"
            identity = None
            if replay:
                manifest = config.output_dir / args.period / "manifest.json"
                identity = json.loads(manifest.read_text())["model"]
            model = Ollama(config.llm, config.output_dir / "cache", replay=replay, identity=identity)
            if not replay:
                print("Local model:", model.inspect(), flush=True)
            print(json.dumps(save_run(config, model, args.period, replay), indent=2))
        elif args.command == "evaluate":
            from .evaluation import compare
            for result in compare(config, args.period):
                print(f"{result['strategy']:8s} {result['cost_bps_per_side']:2g} bp: return {result['net_return']:.2%}, trades {result['trade_count']}")
        elif args.command == "report":
            from .report import generate_report
            print(generate_report(config, args.period))
    except (ValueError, OSError, requests.RequestException) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
