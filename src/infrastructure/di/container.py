"""Dependency Injection Container.

Sprint 57 Feature 57.6: Central DI container for service registration.
Replaces singleton patterns and enables testing with mocks.

This container provides:
- Type-safe service registration and resolution
- Singleton and transient lifetimes
- Async factory support
- Easy testing through reset() and override

Example:
    >>> from src.infrastructure.di import Container, resolve
    >>> from src.domains.knowledge_graph.protocols import GraphStorage
    >>>
    >>> container = Container.get()
    >>> container.register(GraphStorage, Neo4jStorage.create, singleton=True)
    >>>
    >>> storage = await resolve(GraphStorage)
"""

import asyncio
import structlog
from typing import Type, TypeVar, Any, Callable, Awaitable

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class Container:
    """Simple dependency injection container.

    Thread-safe singleton container for managing service registrations
    and resolving dependencies.

    Usage:
        container = Container.get()
        container.register(Interface, factory_func, singleton=True)
        instance = await container.resolve(Interface)
    """

    _instance: "Container | None" = None
    _registrations: dict[Type, tuple[Callable, bool]]
    _singletons: dict[Type, Any]

    def __init__(self) -> None:
        """Initialize container with empty registrations."""
        self._registrations = {}
        self._singletons = {}

    @classmethod
    def get(cls) -> "Container":
        """Get container singleton.

        Returns:
            The global Container instance
        """
        if cls._instance is None:
            cls._instance = Container()
        return cls._instance

    def register(
        self,
        interface: Type[T],
        factory: Callable[[], T | Awaitable[T]],
        singleton: bool = True,
    ) -> None:
        """Register a service factory.

        Args:
            interface: The protocol/interface type to register
            factory: Factory function that creates the implementation
            singleton: If True, only one instance is created (default)

        Example:
            container.register(GraphStorage, Neo4jStorage.create, singleton=True)
        """
        self._registrations[interface] = (factory, singleton)
        logger.debug(
            "service_registered",
            interface=interface.__name__,
            singleton=singleton,
        )

    async def resolve(self, interface: Type[T]) -> T:
        """Resolve a service instance.

        Args:
            interface: The protocol/interface type to resolve

        Returns:
            An instance implementing the interface

        Raises:
            KeyError: If no registration exists for the interface
        """
        # Check for cached singleton
        if interface in self._singletons:
            return self._singletons[interface]

        # Check for registration
        if interface not in self._registrations:
            raise KeyError(f"No registration for {interface.__name__}")

        factory, is_singleton = self._registrations[interface]

        # Create instance
        if asyncio.iscoroutinefunction(factory):
            instance = await factory()
        else:
            instance = factory()

        # Cache if singleton
        if is_singleton:
            self._singletons[interface] = instance
            logger.debug(
                "singleton_created",
                interface=interface.__name__,
            )

        return instance

    def is_registered(self, interface: Type) -> bool:
        """Check if an interface is registered.

        Args:
            interface: The interface type to check

        Returns:
            True if registered
        """
        return interface in self._registrations

    def reset(self) -> None:
        """Reset container, clearing all singletons.

        Use this in tests to start with a clean state.
        """
        self._singletons.clear()
        logger.debug("container_reset")

    def clear(self) -> None:
        """Clear all registrations and singletons.

        Use this for complete reset including registrations.
        """
        self._registrations.clear()
        self._singletons.clear()
        logger.debug("container_cleared")

    def override(
        self,
        interface: Type[T],
        factory: Callable[[], T | Awaitable[T]],
    ) -> None:
        """Override a registration (for testing).

        Clears any existing singleton and registers new factory.

        Args:
            interface: The interface type to override
            factory: New factory function
        """
        if interface in self._singletons:
            del self._singletons[interface]
        self._registrations[interface] = (factory, False)  # Don't cache in tests
        logger.debug(
            "service_overridden",
            interface=interface.__name__,
        )


# Convenience functions
def get_container() -> Container:
    """Get the global container instance.

    Returns:
        The Container singleton
    """
    return Container.get()


async def resolve(interface: Type[T]) -> T:
    """Resolve a service from the global container.

    Args:
        interface: The interface type to resolve

    Returns:
        An instance implementing the interface

    Example:
        storage = await resolve(GraphStorage)
    """
    return await Container.get().resolve(interface)


def register(
    interface: Type[T],
    factory: Callable[[], T | Awaitable[T]],
    singleton: bool = True,
) -> None:
    """Register a service in the global container.

    Args:
        interface: The protocol/interface type
        factory: Factory function
        singleton: Whether to cache instance (default True)

    Example:
        register(GraphStorage, Neo4jStorage.create)
    """
    Container.get().register(interface, factory, singleton)
