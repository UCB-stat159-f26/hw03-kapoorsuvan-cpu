"""Keep all automated tests offline and use a noninteractive plotting backend."""

import socket

import matplotlib
import pytest

matplotlib.use("Agg")


def _block_network(*args, **kwargs):
    """Fail immediately if a test attempts a real network operation."""
    raise AssertionError("Network access is disabled during tests; mock HTTP responses instead.")


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Block name resolution and socket connections while allowing HTTP mocks."""
    monkeypatch.setattr(socket, "getaddrinfo", _block_network)
    monkeypatch.setattr(socket, "create_connection", _block_network)
    monkeypatch.setattr(socket.socket, "connect", _block_network)
    monkeypatch.setattr(socket.socket, "connect_ex", _block_network)
