#!/usr/bin/env python3
"""Entry point for the AWS Interactive Shell."""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aws_shell.app import AWSShell


def main():
    parser = argparse.ArgumentParser(description="AWS Interactive Shell")
    parser.add_argument("--config", type=str, default=None, help="Path to config YAML file")
    parser.add_argument("mode", nargs="?", default=None, choices=["py", "python"],
                        help="Start directly in Python REPL mode")
    args = parser.parse_args()
    shell = AWSShell(config_path=args.config)
    shell.run(start_in_python=args.mode in ("py", "python"))


if __name__ == "__main__":
    main()
