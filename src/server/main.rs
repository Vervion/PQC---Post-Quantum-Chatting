//! PQC Chat Server - Main Entry Point
//!
//! TCP TLS listener for signaling with post-quantum key exchange.

use anyhow::Result;
use clap::Parser;
use log::{error, info};
use parking_lot::RwLock;
use std::collections::HashMap;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;
use tokio_rustls::rustls::{self, pki_types::PrivateKeyDer};
use tokio_rustls::TlsAcceptor;
use uuid::Uuid;

use pqc_chat::crypto::kyber::KyberKeyExchange;
use pqc_chat::media::MediaForwarder;
use pqc_chat::protocol::{ParticipantInfo, RoomInfo, SignalingMessage};
use pqc_chat::room::{Participant, RoomManager};
use pqc_chat::ServerConfig;

/// Command-line arguments
#[derive(Parser, Debug)]
#[command(name = "pqc-server")]
#[command(about = "PQC Chat Server - Post-Quantum Secure Chat")]
struct Args {
    /// Configuration file path
    #[arg(short, long, default_value = "config/server.toml")]
    config: PathBuf,

    /// Override host to bind to
    #[arg(long)]
    host: Option<String>,

    /// Override signaling port
    #[arg(short, long)]
    port: Option<u16>,

    /// Log level
    #[arg(long, default_value = "info")]
    log_level: String,
}

/// Client connection state
#[allow(dead_code)]
struct ClientState {
    participant_id: String,
    username: Option<String>,
    kyber: KyberKeyExchange,
    shared_secret: Option<Vec<u8>>,
}

impl ClientState {
    fn new() -> Self {
        Self {
            participant_id: Uuid::new_v4().to_string(),
            username: None,
            kyber: KyberKeyExchange::new(),
            shared_secret: None,
        }
    }
}

/// Server state
struct ServerState {
    room_manager: RoomManager,
    media_forwarder: RwLock<MediaForwarder>,
    clients: RwLock<HashMap<String, Arc<RwLock<ClientState>>>>,
}

impl ServerState {
    fn new(audio_port: u16, video_port: u16) -> Self {
        Self {
            room_manager: RoomManager::new(),
            media_forwarder: RwLock::new(MediaForwarder::new(audio_port, video_port)),
            clients: RwLock::new(HashMap::new()),
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    // Initialize logging
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or(&args.log_level))
        .init();

    // Load configuration
    let config = if args.config.exists() {
        ServerConfig::from_file(args.config.to_str().unwrap())?
    } else {
        info!("Config file not found, using defaults");
        ServerConfig::default()
    };

    let host = args.host.unwrap_or(config.signaling_host.clone());
    let port = args.port.unwrap_or(config.signaling_port);

    // Load TLS certificates
    let certs = load_certs(&config.certfile)?;
    let key = load_key(&config.keyfile)?;

    // Configure TLS
    let tls_config = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(certs, key)?;

    let acceptor = TlsAcceptor::from(Arc::new(tls_config));

    // Create server state
    let state = Arc::new(ServerState::new(config.audio_port, config.video_port));

    // Start media forwarder
    state.media_forwarder.write().start()?;

    // Bind TCP listener
    let addr: SocketAddr = format!("{}:{}", host, port).parse()?;
    let listener = TcpListener::bind(addr).await?;
    info!("PQC Chat Server listening on {}", addr);

    // Accept connections
    loop {
        let (stream, peer_addr) = listener.accept().await?;
        let acceptor = acceptor.clone();
        let state = state.clone();

        tokio::spawn(async move {
            match acceptor.accept(stream).await {
                Ok(tls_stream) => {
                    info!("New TLS connection from {}", peer_addr);
                    if let Err(e) = handle_client(tls_stream, peer_addr, state).await {
                        error!("Client {} error: {}", peer_addr, e);
                    }
                }
                Err(e) => {
                    error!("TLS handshake failed for {}: {}", peer_addr, e);
                }
            }
        });
    }
}

/// Handle a connected client
async fn handle_client<S>(
    mut stream: tokio_rustls::server::TlsStream<S>,
    peer_addr: SocketAddr,
    state: Arc<ServerState>,
) -> Result<()>
where
    S: tokio::io::AsyncRead + tokio::io::AsyncWrite + Unpin,
{
    let client_state = Arc::new(RwLock::new(ClientState::new()));
    let participant_id = client_state.read().participant_id.clone();

    // Register client
    state
        .clients
        .write()
        .insert(participant_id.clone(), client_state.clone());

    let result = async {
        loop {
            // Read message length (4 bytes)
            let mut len_buf = [0u8; 4];
            if stream.read_exact(&mut len_buf).await.is_err() {
                break;
            }

            let msg_len = u32::from_be_bytes(len_buf) as usize;
            if msg_len > 1024 * 1024 {
                error!("Message too large from {}", peer_addr);
                break;
            }

            // Read message
            let mut msg_buf = vec![0u8; msg_len];
            if stream.read_exact(&mut msg_buf).await.is_err() {
                break;
            }

            // Parse and handle message
            match SignalingMessage::from_bytes(&msg_buf) {
                Ok(message) => {
                    let response =
                        handle_message(message, &participant_id, &client_state, &state).await;
                    
                    // Send response
                    let response_data = response.to_framed()?;
                    stream.write_all(&response_data).await?;
                }
                Err(e) => {
                    error!("Invalid message from {}: {}", peer_addr, e);
                    let error_msg = SignalingMessage::Error {
                        message: "Invalid message format".to_string(),
                    };
                    let data = error_msg.to_framed()?;
                    stream.write_all(&data).await?;
                }
            }
        }
        Ok::<(), anyhow::Error>(())
    }
    .await;

    // Cleanup
    state.clients.write().remove(&participant_id);
    let _ = state.room_manager.leave_room(&participant_id);
    info!("Client {} disconnected", peer_addr);

    result
}

/// Handle a signaling message
async fn handle_message(
    message: SignalingMessage,
    participant_id: &str,
    client_state: &Arc<RwLock<ClientState>>,
    state: &Arc<ServerState>,
) -> SignalingMessage {
    match message {
        SignalingMessage::Login { username } => {
            client_state.write().username = Some(username.clone());
            info!("User {} logged in as {}", participant_id, username);
            SignalingMessage::LoginResponse {
                success: true,
                participant_id: Some(participant_id.to_string()),
                error: None,
            }
        }

        SignalingMessage::KeyExchangeInit { public_key } => {
            // Receive client's public key and encapsulate
            match KyberKeyExchange::public_key_from_bytes(&public_key) {
                Ok(client_pk) => {
                    let (ciphertext, shared_secret) = KyberKeyExchange::encapsulate(&client_pk);
                    client_state.write().shared_secret = Some(shared_secret);
                    info!("Kyber key exchange completed for {}", participant_id);
                    SignalingMessage::KeyExchangeResponse { ciphertext }
                }
                Err(e) => SignalingMessage::Error {
                    message: format!("Key exchange failed: {}", e),
                },
            }
        }

        SignalingMessage::ListRooms => {
            let rooms: Vec<RoomInfo> = state
                .room_manager
                .list_rooms()
                .iter()
                .map(|r| RoomInfo {
                    id: r.id.clone(),
                    name: r.name.clone(),
                    participants: r.participant_count() as u32,
                    max_participants: r.max_participants,
                    is_locked: r.is_locked,
                })
                .collect();
            SignalingMessage::RoomList { rooms }
        }

        SignalingMessage::CreateRoom {
            name,
            max_participants,
        } => {
            let room = state
                .room_manager
                .create_room(name.clone(), max_participants.unwrap_or(10));
            SignalingMessage::RoomCreated {
                success: true,
                room_id: Some(room.id.clone()),
                room_name: Some(room.name.clone()),
                error: None,
            }
        }

        SignalingMessage::JoinRoom { room_id, username } => {
            let participant = Participant::new(participant_id.to_string(), username);

            match state.room_manager.join_room(&room_id, participant) {
                Ok(room) => {
                    let participants: Vec<ParticipantInfo> = room
                        .get_participants()
                        .iter()
                        .map(|p| ParticipantInfo {
                            id: p.id.clone(),
                            username: p.username.clone(),
                            audio_enabled: p.audio_enabled,
                            video_enabled: p.video_enabled,
                        })
                        .collect();

                    SignalingMessage::RoomJoined {
                        success: true,
                        room_id: Some(room.id.clone()),
                        room_name: Some(room.name.clone()),
                        participants: Some(participants),
                        error: None,
                    }
                }
                Err(e) => SignalingMessage::RoomJoined {
                    success: false,
                    room_id: None,
                    room_name: None,
                    participants: None,
                    error: Some(e.to_string()),
                },
            }
        }

        SignalingMessage::LeaveRoom => match state.room_manager.leave_room(participant_id) {
            Ok(()) => SignalingMessage::RoomLeft {
                success: true,
                error: None,
            },
            Err(e) => SignalingMessage::RoomLeft {
                success: false,
                error: Some(e.to_string()),
            },
        },

        SignalingMessage::ToggleAudio { enabled } => {
            if let Some(room) = state.room_manager.get_participant_room(participant_id) {
                room.set_participant_audio(participant_id, enabled);
            }
            SignalingMessage::AudioToggled {
                participant_id: participant_id.to_string(),
                enabled,
            }
        }

        SignalingMessage::ToggleVideo { enabled } => {
            if let Some(room) = state.room_manager.get_participant_room(participant_id) {
                room.set_participant_video(participant_id, enabled);
            }
            SignalingMessage::VideoToggled {
                participant_id: participant_id.to_string(),
                enabled,
            }
        }

        _ => SignalingMessage::Error {
            message: "Unsupported message type".to_string(),
        },
    }
}

/// Load TLS certificates
fn load_certs(path: &PathBuf) -> Result<Vec<rustls::pki_types::CertificateDer<'static>>> {
    let file = std::fs::File::open(path)?;
    let mut reader = std::io::BufReader::new(file);
    let certs = rustls_pemfile::certs(&mut reader).collect::<Result<Vec<_>, _>>()?;
    Ok(certs)
}

/// Load TLS private key
fn load_key(path: &PathBuf) -> Result<PrivateKeyDer<'static>> {
    let file = std::fs::File::open(path)?;
    let mut reader = std::io::BufReader::new(file);
    let keys = rustls_pemfile::private_key(&mut reader)?;
    keys.ok_or_else(|| anyhow::anyhow!("No private key found"))
}
