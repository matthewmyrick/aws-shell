"""CLI entry point for aws-shell."""
import argparse

from .app import AWSShell


def main():
    parser = argparse.ArgumentParser(description="AWS Interactive Shell")
    parser.add_argument("--config", type=str, default=None, help="Path to config YAML file")
    args = parser.parse_args()
    shell = AWSShell(config_path=args.config)
    shell.run()


if __name__ == "__main__":
    main()
