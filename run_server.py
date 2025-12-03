#!/usr/bin/env python3
"""
PQC Chat Server Runner

Main entry point for running the PQC Chat server.
"""

import argparse
import configparser
import logging
import signal
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.server import PQCChatServer, ServerConfig


def parse_config(config_file: str) -> ServerConfig:
    """Parse configuration file."""
    config = configparser.ConfigParser()
    config.read(config_file)
    
    return ServerConfig(
        certfile=config.get('tls', 'certfile', fallback='server.crt'),
        keyfile=config.get('tls', 'keyfile', fallback='server.key'),
        ca_certfile=config.get('tls', 'ca_certfile', fallback=None) or None,
        signaling_host=config.get('server', 'signaling_host', fallback='0.0.0.0'),
        signaling_port=config.getint('server', 'signaling_port', fallback=8443),
        media_host=config.get('server', 'media_host', fallback='0.0.0.0'),
        audio_port=config.getint('server', 'audio_port', fallback=10000),
        video_port=config.getint('server', 'video_port', fallback=10001),
    )


def setup_logging(level: str = 'INFO', log_file: str = None):
    """Set up logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='PQC Chat Server')
    parser.add_argument(
        '--config', '-c',
        default='config/server.conf',
        help='Configuration file path'
    )
    parser.add_argument(
        '--host',
        help='Override bind host'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        help='Override signaling port'
    )
    parser.add_argument(
        '--cert',
        help='Override certificate file'
    )
    parser.add_argument(
        '--key',
        help='Override key file'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Load configuration
    if os.path.exists(args.config):
        config = parse_config(args.config)
    else:
        logger.warning(f"Config file not found: {args.config}, using defaults")
        config = ServerConfig(
            certfile='server.crt',
            keyfile='server.key'
        )
    
    # Apply command-line overrides
    if args.host:
        config.signaling_host = args.host
    if args.port:
        config.signaling_port = args.port
    if args.cert:
        config.certfile = args.cert
    if args.key:
        config.keyfile = args.key
    
    # Check certificates
    if not os.path.exists(config.certfile):
        logger.error(f"Certificate file not found: {config.certfile}")
        logger.info("Generate certificates with: scripts/generate_certs.sh")
        sys.exit(1)
        
    if not os.path.exists(config.keyfile):
        logger.error(f"Key file not found: {config.keyfile}")
        sys.exit(1)
    
    # Create and start server
    server = PQCChatServer(config)
    
    # Set up signal handlers
    def shutdown_handler(signum, frame):
        logger.info("Received shutdown signal")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    logger.info(f"Starting PQC Chat Server on {config.signaling_host}:{config.signaling_port}")
    
    try:
        server.start()
        
        # Keep running
        signal.pause()
        
    except Exception as e:
        logger.error(f"Server error: {e}")
        server.stop()
        sys.exit(1)


if __name__ == '__main__':
    main()
