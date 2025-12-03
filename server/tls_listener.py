"""
TCP TLS Listener for Signaling

Provides a secure TLS-wrapped TCP server for handling client signaling
connections with post-quantum key exchange support.
"""

import socket
import ssl
import threading
import logging
from typing import Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TLSConfig:
    """Configuration for TLS listener."""
    certfile: str
    keyfile: str
    host: str = "0.0.0.0"
    port: int = 8443
    ca_certfile: Optional[str] = None


class TLSListener:
    """
    TCP TLS listener for signaling connections.
    
    This listener accepts incoming TLS connections from clients
    and dispatches them to registered handlers.
    """
    
    def __init__(self, config: TLSConfig):
        """
        Initialize the TLS listener.
        
        Args:
            config: TLS configuration including certificates and bind address.
        """
        self.config = config
        self._server_socket: Optional[socket.socket] = None
        self._ssl_context: Optional[ssl.SSLContext] = None
        self._running = False
        self._accept_thread: Optional[threading.Thread] = None
        self._on_connection: Optional[Callable[[ssl.SSLSocket, tuple], None]] = None
        self._client_threads: list[threading.Thread] = []
        
    def setup_ssl_context(self) -> ssl.SSLContext:
        """
        Create and configure the SSL context.
        
        Returns:
            Configured SSL context for server-side TLS.
        """
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(
            certfile=self.config.certfile,
            keyfile=self.config.keyfile
        )
        
        if self.config.ca_certfile:
            context.load_verify_locations(self.config.ca_certfile)
            context.verify_mode = ssl.CERT_REQUIRED
        else:
            context.verify_mode = ssl.CERT_NONE
            
        return context
    
    def set_connection_handler(self, handler: Callable[[ssl.SSLSocket, tuple], None]):
        """
        Set the handler for new connections.
        
        Args:
            handler: Callback function receiving (ssl_socket, address) tuple.
        """
        self._on_connection = handler
        
    def start(self):
        """Start the TLS listener."""
        if self._running:
            logger.warning("TLS listener already running")
            return
            
        self._ssl_context = self.setup_ssl_context()
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.config.host, self.config.port))
        self._server_socket.listen(5)
        
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()
        
        logger.info(f"TLS listener started on {self.config.host}:{self.config.port}")
        
    def stop(self):
        """Stop the TLS listener."""
        self._running = False
        
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")
            self._server_socket = None
            
        if self._accept_thread:
            self._accept_thread.join(timeout=5.0)
            self._accept_thread = None
            
        logger.info("TLS listener stopped")
        
    def _accept_loop(self):
        """Main loop for accepting connections."""
        while self._running:
            try:
                client_socket, address = self._server_socket.accept()
                ssl_socket = self._ssl_context.wrap_socket(
                    client_socket,
                    server_side=True
                )
                
                logger.info(f"New TLS connection from {address}")
                
                if self._on_connection:
                    client_thread = threading.Thread(
                        target=self._on_connection,
                        args=(ssl_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                    self._client_threads.append(client_thread)
                else:
                    ssl_socket.close()
                    
            except ssl.SSLError as e:
                if self._running:
                    logger.error(f"SSL error during handshake: {e}")
            except OSError as e:
                if self._running:
                    logger.error(f"Socket error: {e}")
            except Exception as e:
                if self._running:
                    logger.error(f"Error accepting connection: {e}")
                    
    @property
    def is_running(self) -> bool:
        """Check if the listener is running."""
        return self._running
