import argparse
import os
import base64
import logging
import grpc
from dotenv import load_dotenv

import seabird_pb2
import seabird_pb2_grpc
from interceptor import add_header
from runescape import level_callback, pretty_suffix, pretty_thousands

LOG = logging.getLogger("runescape-plugin")
ch = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s %(asctime)s %(name)s] %(message)s")
ch.setFormatter(formatter)
LOG.addHandler(ch)

load_dotenv()


def handle_level(stub, identity, command):
    level_callback(
        stub, identity, command, "level", "level {value} {skill}", str,
    )


def handle_experience(stub, identity, command) -> None:
    level_callback(
        stub,
        identity,
        command,
        "experience",
        "{value} experience in {skill}",
        pretty_suffix,
    )


def handle_rank(stub, identity, command) -> None:
    level_callback(
        stub, identity, command, "rank", "rank {value} in {skill}", pretty_thousands,
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Log more verbosely",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.verbose:
        LOG.setLevel("DEBUG")
    else:
        LOG.setLevel("INFO")

    host_port = os.getenv("HOST_PORT")
    if host_port is None:
        LOG.error("Missing $HOST_PORT setting")
        return

    token = os.getenv("TOKEN")
    if token is None:
        LOG.error("Missing $TOKEN setting")
        return

    with grpc.secure_channel(host_port, grpc.ssl_channel_credentials()) as channel:
        stub = seabird_pb2_grpc.SeabirdStub(channel)

        LOG.info("Connection established with seabird core at %s", host_port)

        identity = seabird_pb2.Identity(token=token,)

        for event in stub.StreamEvents(
            seabird_pb2.StreamEventsRequest(
                identity=identity,
                commands={
                    "rlvl": seabird_pb2.CommandMetadata(
                        name="rlvl",
                        short_help="Old-School RuneScape level information",
                        full_help="Get an Old-School RuneScape character's level(s)",
                    ),
                    "rexp": seabird_pb2.CommandMetadata(
                        name="rexp",
                        short_help="Old-School RuneScape experience information",
                        full_help="Get an Old-School RuneScape character's experience in a skill",
                    ),
                    "rrank": seabird_pb2.CommandMetadata(
                        name="rrank",
                        short_help="Old-School RuneScape rank information",
                        full_help="Get an Old-School RuneScape character's rank in a skill",
                    ),
                },
            )
        ):
            command = event.command
            if not command:
                continue

            LOG.debug("Received command %s", command)
            if command.command == "rlvl":
                handle_level(stub, identity, command)
            elif command.command == "rexp":
                handle_experience(stub, identity, command)
            elif command.command == "rrank":
                handle_rank(stub, identity, command)


main()
