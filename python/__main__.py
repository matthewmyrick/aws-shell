#!/usr/bin/env python3
"""Entry point for the AWS Interactive Shell."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aws_shell.app import AWSShell


def main():
    shell = AWSShell()
    shell.run()


if __name__ == "__main__":
    main()
