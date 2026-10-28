"""Loads local.env from the repository root into os.environ (README: Local configuration).

local.env is not in the repository (.gitignore): copy local.env.example and set your own addresses.
One KEY=VALUE per line, # starts a comment, ~ is expanded. Variables already set in the environment
win, so `PICO_LINK=phone python3 pico_dev.py ...` still overrides the file.
"""
import os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'local.env')


def load(path=PATH):
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), os.path.expanduser(value.strip().strip('"\'')))


load()
