"""Label Lens command line.

    python lookup.py ibuprofen                 # print the official label sections
    python lookup.py Zyrtec --explain          # plain-language explanation
    python lookup.py metformin --explain --language Spanish
"""

import argparse
import sys

from label_lens.fda import DrugNotFound, label_info, search_label


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("drug", help="Brand or generic name, e.g. Advil or ibuprofen")
    parser.add_argument("--explain", action="store_true", help="Explain the label in plain language")
    parser.add_argument("--language", default="English", help="Language for the explanation")
    args = parser.parse_args()

    try:
        info = label_info(search_label(args.drug))
    except DrugNotFound as e:
        sys.exit(str(e))

    print(f"{info['brand_name'] or '?'} ({info['generic_name'] or '?'}) by {info['manufacturer'] or '?'}\n")
    if args.explain:
        from label_lens.explain import explain_label

        print(explain_label(info, language=args.language))
    else:
        for title, text in info["sections"].items():
            print(f"== {title} ==\n{text}\n")


if __name__ == "__main__":
    main()
