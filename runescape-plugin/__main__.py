import argparse
import base64
import logging
import grpc

import seabird_pb2
import seabird_pb2_grpc
import config
from interceptor import add_header
from runescape import level_callback, pretty_suffix, pretty_thousands

LOG = logging.getLogger("runescape-plugin")
ch = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s %(asctime)s %(name)s] %(message)s")
ch.setFormatter(formatter)
LOG.addHandler(ch)


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

    with grpc.secure_channel(
        config.host_port, grpc.ssl_channel_credentials()
    ) as channel:
        channel = grpc.intercept_channel(
            channel,
            add_header(
                "authorization",
                "Basic {}".format(
                    base64.b64encode(
                        f"{config.username}:{config.password}".encode("utf-8")
                    ).decode("utf-8")
                ),
            ),
        )
        stub = seabird_pb2_grpc.SeabirdStub(channel)

        response, _ = stub.OpenSession.with_call(
            seabird_pb2.OpenSessionRequest(
                plugin="runescape",
                commands={
                    "rlvl": seabird_pb2.CommandMetadata(
                        name="rlvl",
                        shortHelp="Old-School RuneScape level information",
                        fullHelp="Get an Old-School RuneScape character's level(s)",
                    ),
                    "rexp": seabird_pb2.CommandMetadata(
                        name="rexp",
                        shortHelp="Old-School RuneScape experience information",
                        fullHelp="Get an Old-School RuneScape character's experience in a skill",
                    ),
                    "rrank": seabird_pb2.CommandMetadata(
                        name="rrank",
                        shortHelp="Old-School RuneScape rank information",
                        fullHelp="Get an Old-School RuneScape character's rank in a skill",
                    ),
                },
            )
        )

        LOG.info("Connection established with seabird core at %s", config.host_port)

        identity = response.identity
        for event in stub.Events(seabird_pb2.EventsRequest(identity=identity)):
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
