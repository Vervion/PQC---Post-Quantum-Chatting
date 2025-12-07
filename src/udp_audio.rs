//! UDP Audio Streaming for Real-Time Communication
//!
//! High-performance UDP-based audio streaming that prioritizes low latency
//! over guaranteed delivery. Perfect for real-time voice communication.

use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::UdpSocket;
use tokio::sync::mpsc;
use anyhow::Result;
use serde::{Serialize, Deserialize};

/// UDP Audio packet format
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UdpAudioPacket {
    pub session_id: String,
    pub sequence: u32,
    pub timestamp: u64, // Microseconds since epoch
    pub audio_data: Vec<u8>,
}

/// UDP Audio Server - handles incoming audio streams
pub struct UdpAudioServer {
    socket: Arc<UdpSocket>,
    port: u16,
}

impl UdpAudioServer {
    pub async fn new(port: u16) -> Result<Self> {
        let addr = format!("0.0.0.0:{}", port);
        let socket = UdpSocket::bind(&addr).await?;
        println!("🚀 UDP Audio Server listening on {}", addr);
        
        Ok(Self {
            socket: Arc::new(socket),
            port,
        })
    }
    
    pub async fn start(&self, audio_tx: mpsc::UnboundedSender<(SocketAddr, UdpAudioPacket)>) -> Result<()> {
        let socket = self.socket.clone();
        
        tokio::spawn(async move {
            let mut buf = [0u8; 2048]; // Sufficient for compressed audio chunks
            
            loop {
                match socket.recv_from(&mut buf).await {
                    Ok((len, src)) => {
                        // Parse UDP audio packet
                        if let Ok(packet) = bincode::deserialize::<UdpAudioPacket>(&buf[..len]) {
                            // Forward to audio processing
                            if audio_tx.send((src, packet)).is_err() {
                                break; // Channel closed
                            }
                        }
                    }
                    Err(e) => {
                        eprintln!("UDP recv error: {}", e);
                        break;
                    }
                }
            }
        });
        
        Ok(())
    }
    
    pub async fn send_audio(&self, target: SocketAddr, packet: &UdpAudioPacket) -> Result<()> {
        let data = bincode::serialize(packet)?;
        self.socket.send_to(&data, target).await?;
        Ok(())
    }
}

/// UDP Audio Client - sends audio streams  
pub struct UdpAudioClient {
    socket: Arc<UdpSocket>,
    server_addr: SocketAddr,
    session_id: String,
    sequence: std::sync::atomic::AtomicU32,
}

impl Clone for UdpAudioClient {
    fn clone(&self) -> Self {
        Self {
            socket: self.socket.clone(),
            server_addr: self.server_addr,
            session_id: self.session_id.clone(),
            sequence: std::sync::atomic::AtomicU32::new(
                self.sequence.load(std::sync::atomic::Ordering::Relaxed)
            ),
        }
    }
}

impl UdpAudioClient {
    pub async fn new(server_addr: SocketAddr, session_id: String) -> Result<Self> {
        let socket = UdpSocket::bind("0.0.0.0:0").await?;
        
        Ok(Self {
            socket: Arc::new(socket),
            server_addr,
            session_id,
            sequence: std::sync::atomic::AtomicU32::new(0),
        })
    }
    
    pub async fn send_audio_chunk(&self, audio_data: Vec<u8>) -> Result<()> {
        let sequence = self.sequence.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)?
            .as_micros() as u64;
            
        let packet = UdpAudioPacket {
            session_id: self.session_id.clone(),
            sequence,
            timestamp,
            audio_data,
        };
        
        let data = bincode::serialize(&packet)?;
        
        // UDP send is non-blocking and doesn't guarantee delivery
        // This is exactly what we want for real-time audio!
        self.socket.send_to(&data, self.server_addr).await?;
        Ok(())
    }
}

/// Audio packet buffer that discards old packets automatically
pub struct RealTimeAudioBuffer {
    max_age_ms: u64,
    packets: std::collections::VecDeque<(u64, Vec<u8>)>, // (timestamp, audio_data)
}

impl RealTimeAudioBuffer {
    pub fn new(max_age_ms: u64) -> Self {
        Self {
            max_age_ms,
            packets: std::collections::VecDeque::with_capacity(10), // Small buffer
        }
    }
    
    pub fn add_packet(&mut self, audio_data: Vec<u8>) {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;
            
        // Remove packets older than max_age_ms
        while let Some((timestamp, _)) = self.packets.front() {
            if now - timestamp > self.max_age_ms {
                self.packets.pop_front();
            } else {
                break;
            }
        }
        
        // Add new packet
        self.packets.push_back((now, audio_data));
        
        // Enforce maximum buffer size (drop oldest if needed)
        if self.packets.len() > 5 {
            self.packets.pop_front();
        }
    }
    
    pub fn get_next_packet(&mut self) -> Option<Vec<u8>> {
        self.packets.pop_front().map(|(_, data)| data)
    }
    
    pub fn buffer_age_ms(&self) -> u64 {
        if let (Some(oldest), Some(newest)) = (self.packets.front(), self.packets.back()) {
            newest.0 - oldest.0
        } else {
            0
        }
    }
    
    pub fn len(&self) -> usize {
        self.packets.len()
    }
}