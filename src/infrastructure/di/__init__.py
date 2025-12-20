"""Dependency Injection Container.

Sprint 57 Feature 57.6: Central DI container for service registration.
Replaces singleton patterns and enables testing with mocks.

Usage:
    from src.infrastructure.di import Container, resolve

    # Register services
    container = Container.get()
    container.register(GraphStorage, Neo4jStorage.create, singleton=True)

    # Resolve services
    storage = await resolve(GraphStorage)

For testing:
    container.reset()  # Clear all singletons
    container.register(GraphStorage, MockStorage, singleton=False)
"""

from src.infrastructure.di.container import (
    Container,
    get_container,
    register,
    resolve,
)

__all__ = [
    "Container",
    "get_container",
    "resolve",
    "register",
]
