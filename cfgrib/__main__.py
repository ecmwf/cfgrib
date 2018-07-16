
import argparse
import sys

from . import eccodes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--selfcheck', default=False, action='store_true')
    args = parser.parse_args()
    if args.selfcheck:
        eccodes.codes_get_api_version()
        print("Your system is ready.")
    else:
        raise RuntimeError("Command not recognised. See usage with --help.")


if __name__ == '__main__':
    main()
