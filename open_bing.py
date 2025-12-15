"""
Simple script to launch Bing in the system's default web browser.
"""

import webbrowser


def main() -> None:
    webbrowser.open("https://www.bing.com", new=2)  # new=2 tries to open in a new tab


if __name__ == "__main__":
    main()







