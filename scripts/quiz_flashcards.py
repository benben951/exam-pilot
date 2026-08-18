import argparse
import json
import random
from pathlib import Path


def load_cards(path):
    cards = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                cards.append(json.loads(line))
    return cards


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cards", required=True)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--show-answers", action="store_true")
    args = parser.parse_args()

    cards = load_cards(args.cards)
    sample = random.sample(cards, min(args.count, len(cards)))

    for idx, card in enumerate(sample, 1):
        print(f"\n[{idx}] {card['front']}")
        print(f"Subject: {card['subject']} | Topic: {card['topic']} | Source: {card['source']}")
        if args.show_answers:
            print(f"Answer: {card['back']}")
        else:
            print("Answer: <hidden; rerun with --show-answers>")


if __name__ == "__main__":
    main()
