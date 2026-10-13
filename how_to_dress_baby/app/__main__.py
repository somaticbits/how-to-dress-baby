import argparse
import logging
from pathlib import Path

from app.config import load_config
from app.render import render
from app.server import serve
from app.weather import demo_snapshot, utc_now


def main() -> None:
    parser = argparse.ArgumentParser(description="Local baby clothing image for Kindle")
    parser.add_argument("--config", help="JSON config file (default: add-on options or demo)")
    parser.add_argument("--render-demo", metavar="PNG", help="Render labelled sample PNG and exit")
    parser.add_argument("--page", choices=("auto", "day", "night"), default="auto")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config(args.config)
    if args.render_demo:
        now = utc_now()
        destination = Path(args.render_demo)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(render(demo_snapshot(now), config, now, page=args.page))
        print(destination)
    else:
        serve(config)


if __name__ == "__main__":
    main()
