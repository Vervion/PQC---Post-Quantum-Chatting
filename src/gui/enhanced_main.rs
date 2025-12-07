//! Enhanced PQC Chat GUI - Real-time User Management
//!
//! Advanced GUI with live user tracking and real server communication

#[cfg(feature = "gui")]
use eframe::egui;
#[cfg(feature = "gui")]
use std::collections::HashMap;
#[cfg(feature = "gui")]
use std::sync::{Arc, Mutex};
#[cfg(feature = "gui")]
use tokio::sync::mpsc;
#[cfg(feature = "gui")]
use tokio::runtime::Runtime;
#[cfg(feature = "gui")]
use tokio::io::{AsyncReadExt, AsyncWriteExt};

#[cfg(feature = "gui")]
use pqc_chat::crypto::kyber::KyberKeyExchange;
#[cfg(feature = "gui")]
use pqc_chat::protocol::{ParticipantInfo, RoomInfo, SignalingMessage};
#[cfg(feature = "gui")]
use pqc_chat::udp_audio::{UdpAudioClient, RealTimeAudioBuffer};

// Helper function for formatting timestamps
fn format_time(time: std::time::SystemTime) -> String {
    if let Ok(duration) = time.duration_since(std::time::UNIX_EPOCH) {
        let secs = duration.as_secs();
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let diff = now.saturating_sub(secs);
        if diff < 60 {
            "now".to_string()
        } else if diff < 3600 {
            format!("{}m ago", diff / 60)
        } else if diff < 86400 {
            format!("{}h ago", diff / 3600)
        } else {
            format!("{}d ago", diff / 86400)
        }
    } else {
        "unknown".to_string()
    }
}


#[cfg(feature = "gui")]
fn main() -> Result<(), eframe::Error> {
    env_logger::init();

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1000.0, 700.0])
            .with_min_inner_size([800.0, 600.0])
            .with_title("PQC Chat - Post-Quantum Secure"),
        ..Default::default()
    };

    eframe::run_native(
        "PQC Chat - Enhanced",
        options,
        Box::new(|cc| Box::new(EnhancedPqcChatApp::new(cc))),
    )
}

#[cfg(not(feature = "gui"))]
fn main() {
    eprintln!("GUI feature not enabled. Build with: cargo build --features gui");
}

#[cfg(feature = "gui")]
#[derive(Debug, Clone)]
struct ChatMessage {
    sender_id: String,
    sender_username: String,
    content: String,
    timestamp: std::time::SystemTime,
}

#[cfg(feature = "gui")]
#[derive(Debug, Clone)]
struct ConnectedUser {
    id: String,
    username: String,
    connected_at: std::time::SystemTime,
    in_room: Option<String>,
    audio_enabled: bool,
    video_enabled: bool,
}

#[cfg(feature = "gui")]
#[derive(Clone)]
struct RoomData {
    id: String,
    name: String,
    participants: u32,
    max_participants: u32,
    is_locked: bool,
}

#[cfg(feature = "gui")]
struct EnhancedPqcChatApp {
    // Connection state
    server_host: String,
    server_port: String,
    username: String,
    is_connected: bool,
    connection_status: String,

    // Room state
    rooms: Vec<RoomData>,
    current_room: Option<RoomData>,
    selected_room_idx: Option<usize>,
    new_room_name: String,
    room_participants: Vec<ParticipantInfo>,

    // User management
    connected_users: HashMap<String, ConnectedUser>,
    user_list_scroll: f32,

    // Media state
    audio_enabled: bool,
    video_enabled: bool,
    audio_call_active: bool,
    audio_manager: Option<Arc<Mutex<pqc_chat::audio::AudioManager>>>,
    audio_producer: Option<Arc<Mutex<ringbuf::HeapProducer<f32>>>>,
    audio_send_handle: Option<std::thread::JoinHandle<()>>,
    audio_packet_counter: u32,  // For aggressive latency control
    last_buffer_reset: std::time::SystemTime,  // Track when we last reset buffers
    consecutive_high_buffer: u32,  // Count of high buffer usage events
    buffer_usage: f32,  // Current buffer usage percentage
    estimated_latency_ms: usize,  // Estimated audio latency in milliseconds
    
    // UDP Audio for ultra-low latency streaming
    udp_audio_client: Option<UdpAudioClient>,
    real_time_buffer: RealTimeAudioBuffer,
    use_udp_audio: bool,  // Toggle between TCP and UDP audio

    // Chat state - per room
    room_chat_history: HashMap<String, Vec<ChatMessage>>,  // room_id -> messages
    message_input: String,
    
    // UI state
    show_users_panel: bool,
    show_rooms_panel: bool,
    users_window_open: bool,
    status_messages: Vec<(String, std::time::SystemTime)>,
    
    // Communication
    runtime: Option<Arc<Runtime>>,
    command_sender: Option<mpsc::UnboundedSender<GuiCommand>>,
    update_receiver: Option<Arc<Mutex<mpsc::UnboundedReceiver<GuiUpdate>>>>,
}

#[cfg(feature = "gui")]
#[derive(Debug)]
enum GuiCommand {
    Connect { host: String, port: u16, username: String },
    Disconnect,
    ListRooms,
    CreateRoom { name: String, max_participants: u32 },
    JoinRoom { room_id: String },
    LeaveRoom,
    ToggleAudio { enabled: bool },
    ToggleVideo { enabled: bool },
    // Server-wide user management
    ListServerUsers,
    // Chat functionality
    SendMessage { content: String },
    // Audio call functionality
    StartAudioCall,
    StopAudioCall,
    SendAudioData { data: Vec<u8> },
    SendUdpAudioData { data: Vec<u8> },  // Ultra-low latency UDP audio
    InitializeUdpAudio { host: String, port: u16 },  // Initialize UDP audio client
}

#[cfg(feature = "gui")]
#[derive(Debug, Clone)]
enum GuiUpdate {
    Connected { participant_id: String },
    Disconnected,
    ConnectionError { error: String },
    RoomList { rooms: Vec<RoomInfo> },
    RoomJoined { room: RoomInfo, participants: Vec<ParticipantInfo> },
    RoomLeft,
    ParticipantJoined { participant: ParticipantInfo },
    ParticipantLeft { participant_id: String },
    ParticipantAudioToggled { participant_id: String, enabled: bool },
    ParticipantVideoToggled { participant_id: String, enabled: bool },
    // Server-wide user tracking
    ServerUserConnected { user: ConnectedUser },
    ServerUserDisconnected { user_id: String },
    ServerUserList { users: Vec<ConnectedUser> },
    // Chat functionality
    ChatMessageReceived { message: ChatMessage },
    StatusMessage { message: String },
    // Audio functionality
    AudioDataReceived { sender_id: String, data: Vec<u8> },
    UdpAudioClientReady { client: pqc_chat::udp_audio::UdpAudioClient },
}

#[cfg(feature = "gui")]
impl EnhancedPqcChatApp {
    fn new(_cc: &eframe::CreationContext<'_>) -> Self {
        let runtime = Arc::new(
            Runtime::new().expect("Failed to create tokio runtime")
        );

        let (command_sender, command_receiver) = mpsc::unbounded_channel();
        let (update_sender, update_receiver) = mpsc::unbounded_channel();
        let update_receiver = Arc::new(Mutex::new(update_receiver));

        // Spawn the communication task
        let rt = runtime.clone();
        std::thread::spawn(move || {
            rt.block_on(async {
                communication_task(command_receiver, update_sender).await;
            });
        });

        Self {
            server_host: "192.168.10.101".to_string(),
            server_port: "8443".to_string(),
            username: std::env::var("USER").unwrap_or_else(|_| "PiUser".to_string()),
            is_connected: false,
            connection_status: "Disconnected".to_string(),
            rooms: Vec::new(),
            current_room: None,
            selected_room_idx: None,
            new_room_name: String::new(),
            room_participants: Vec::new(),
            connected_users: HashMap::new(),
            user_list_scroll: 0.0,
            room_chat_history: HashMap::new(),
            message_input: String::new(),
            audio_enabled: true,
            video_enabled: true,
            audio_call_active: false,
            audio_manager: None,
            audio_producer: None,
            audio_send_handle: None,
            audio_packet_counter: 0,
            last_buffer_reset: std::time::SystemTime::now(),
            consecutive_high_buffer: 0,
            buffer_usage: 0.0,
            estimated_latency_ms: 0,
            
            // Initialize UDP audio components
            udp_audio_client: None,
            real_time_buffer: RealTimeAudioBuffer::new(150), // 150ms max buffer age
            use_udp_audio: false,  // Temporarily disable UDP until fully integrated
            show_users_panel: true,
            show_rooms_panel: true,
            users_window_open: true,
            status_messages: Vec::new(),
            runtime: Some(runtime),
            command_sender: Some(command_sender),
            update_receiver: Some(update_receiver),
        }
    }

    fn process_updates(&mut self) {
        let updates = if let Some(receiver) = &self.update_receiver {
            let mut receiver = receiver.lock().unwrap();
            let mut updates = Vec::new();
            while let Ok(update) = receiver.try_recv() {
                updates.push(update);
            }
            updates
        } else {
            Vec::new()
        };
        
        for update in updates {
            match update {
                GuiUpdate::Connected { participant_id } => {
                    self.is_connected = true;
                    self.connection_status = format!("Connected as {}", self.username);
                    self.add_status_message("🟢 Connected to server".to_string());
                    
                    // Add ourselves to connected users
                    self.connected_users.insert(participant_id.clone(), ConnectedUser {
                        id: participant_id,
                        username: self.username.clone(),
                        connected_at: std::time::SystemTime::now(),
                        in_room: None,
                        audio_enabled: self.audio_enabled,
                        video_enabled: self.video_enabled,
                    });
                },
                GuiUpdate::Disconnected => {
                    self.is_connected = false;
                    self.connection_status = "Disconnected".to_string();
                    self.rooms.clear();
                    self.current_room = None;
                    self.connected_users.clear();
                    self.room_participants.clear();
                    self.add_status_message("🔴 Disconnected from server".to_string());
                },
                GuiUpdate::ConnectionError { error } => {
                    self.connection_status = format!("Connection Error: {}", error);
                    self.add_status_message(format!("❌ Connection failed: {}", error));
                },
                GuiUpdate::RoomList { rooms } => {
                    self.rooms = rooms.into_iter().map(|r| RoomData {
                        id: r.id,
                        name: r.name,
                        participants: r.participants,
                        max_participants: r.max_participants,
                        is_locked: r.is_locked,
                    }).collect();
                },
                GuiUpdate::RoomJoined { room, participants } => {
                    eprintln!("DEBUG: RoomJoined - received {} participants", participants.len());
                    for (i, p) in participants.iter().enumerate() {
                        eprintln!("DEBUG: Participant {}: {} ({})", i, p.username, p.id);
                    }
                    
                    self.current_room = Some(RoomData {
                        id: room.id.clone(),
                        name: room.name.clone(),
                        participants: room.participants,
                        max_participants: room.max_participants,
                        is_locked: room.is_locked,
                    });
                    self.room_participants = participants;
                    self.add_status_message(format!("🎉 Joined room: {} with {} participants", room.name, self.room_participants.len()));
                },
                GuiUpdate::RoomLeft => {
                    if let Some(room) = &self.current_room {
                        self.add_status_message(format!("👋 Left room: {}", room.name));
                    }
                    self.current_room = None;
                    self.room_participants.clear();
                },
                GuiUpdate::ParticipantJoined { participant } => {
                    eprintln!("DEBUG: ParticipantJoined - {} ({})", participant.username, participant.id);
                    self.room_participants.push(participant.clone());
                    
                    // Update current room participant count
                    if let Some(ref mut room) = self.current_room {
                        room.participants = self.room_participants.len() as u32;
                    }
                    
                    self.add_status_message(format!("🟢 {} joined the room (total: {})", participant.username, self.room_participants.len()));
                },
                GuiUpdate::ParticipantLeft { participant_id } => {
                    // Find the username before removing for the status message
                    let username = self.room_participants.iter()
                        .find(|p| p.id == participant_id)
                        .map(|p| p.username.clone())
                        .unwrap_or_else(|| "User".to_string());
                    
                    self.room_participants.retain(|p| p.id != participant_id);
                    
                    // Update current room participant count
                    if let Some(ref mut room) = self.current_room {
                        room.participants = self.room_participants.len() as u32;
                    }
                    
                    self.add_status_message(format!("🔴 {} left the room (total: {})", username, self.room_participants.len()));
                },
                GuiUpdate::ParticipantAudioToggled { participant_id, enabled } => {
                    if let Some(participant) = self.room_participants.iter_mut().find(|p| p.id == participant_id) {
                        participant.audio_enabled = enabled;
                    }
                    if let Some(user) = self.connected_users.get_mut(&participant_id) {
                        user.audio_enabled = enabled;
                    }
                },
                GuiUpdate::ParticipantVideoToggled { participant_id, enabled } => {
                    if let Some(participant) = self.room_participants.iter_mut().find(|p| p.id == participant_id) {
                        participant.video_enabled = enabled;
                    }
                    if let Some(user) = self.connected_users.get_mut(&participant_id) {
                        user.video_enabled = enabled;
                    }
                },
                GuiUpdate::ServerUserConnected { user } => {
                    self.connected_users.insert(user.id.clone(), user.clone());
                    self.add_status_message(format!("👤 {} connected to server", user.username));
                },
                GuiUpdate::ServerUserDisconnected { user_id } => {
                    if let Some(user) = self.connected_users.remove(&user_id) {
                        self.add_status_message(format!("👤 {} disconnected from server", user.username));
                    }
                },
                GuiUpdate::ServerUserList { users } => {
                    self.connected_users.clear();
                    for user in users {
                        self.connected_users.insert(user.id.clone(), user);
                    }
                },
                GuiUpdate::ChatMessageReceived { message } => {
                    eprintln!("DEBUG: GuiUpdate::ChatMessageReceived - from {} ({}): {}", message.sender_username, message.sender_id, message.content);
                    
                    // Only add message if we're in a room
                    if let Some(ref room) = self.current_room {
                        let room_id = room.id.clone();
                        let chat_history = self.room_chat_history.entry(room_id.clone()).or_insert_with(Vec::new);
                        
                        // Check for duplicate - don't add if we already have this message
                        // (this happens when we optimistically add our own message, then get the broadcast)
                        let is_duplicate = chat_history.iter().any(|m| {
                            m.content == message.content && 
                            m.sender_username == message.sender_username &&
                            m.timestamp.duration_since(message.timestamp).unwrap_or_default().as_secs() < 2
                        });
                        
                        if !is_duplicate {
                            chat_history.push(message);
                            // Keep only last 100 messages per room
                            if chat_history.len() > 100 {
                                chat_history.remove(0);
                            }
                            eprintln!("DEBUG: Added message to room {}. Total messages: {}", room_id, chat_history.len());
                        } else {
                            eprintln!("DEBUG: Skipped duplicate message");
                        }
                    }
                },
                GuiUpdate::StatusMessage { message } => {
                    self.add_status_message(message);
                },
                GuiUpdate::AudioDataReceived { sender_id, data } => {
                    eprintln!("DEBUG: Received {} bytes of audio data from {}", data.len(), sender_id);
                    // ULTRA-LOW LATENCY AUDIO: Immediate processing with aggressive buffer management
                    if let Some(producer) = &self.audio_producer {
                        self.audio_packet_counter += 1;
                        
                        let samples = pqc_chat::audio::bytes_to_samples(&data);
                        let mut producer = producer.lock().unwrap();
                        
                        // CRITICAL: Real-time buffer analysis
                        let buffer_free_space = producer.free_len();
                        let buffer_used_space = producer.len();
                        let total_capacity = buffer_free_space + buffer_used_space;
                        let buffer_usage_percent = (buffer_used_space as f32 / total_capacity as f32) * 100.0;
                        
                        // STRATEGY: Maintain <100ms of buffered audio (4800 samples at 48kHz)
                        let max_latency_samples = 4800; // 100ms maximum buffer
                        let emergency_threshold = 2400; // 50ms - start aggressive clearing
                        
                        // EMERGENCY: Buffer too full - drain old audio immediately
                        if buffer_used_space > max_latency_samples {
                            let samples_to_drain = buffer_used_space - emergency_threshold;
                            eprintln!("EMERGENCY: Draining {} samples to prevent {}ms latency", 
                                     samples_to_drain, (buffer_used_space * 1000) / 48000);
                            
                            // Since we can't access consumer here, we'll clear space by not adding new data
                            // and relying on the consumer to drain the existing buffer
                            self.consecutive_high_buffer += 1;
                            
                            // Only process every Nth packet when buffer is critically full
                            if self.audio_packet_counter % 3 != 0 {
                                return; // Skip this packet to let buffer drain
                            }
                        }
                        
                        // AGGRESSIVE: Even moderate buffer usage triggers packet skipping
                        if buffer_usage_percent > 25.0 {
                            self.consecutive_high_buffer += 1;
                            // Skip 50% of packets when buffer > 25% to prevent buildup
                            if self.audio_packet_counter % 2 == 0 {
                                return;
                            }
                        } else {
                            self.consecutive_high_buffer = 0;
                        }
                        
                        // FORCE IMMEDIATE PROCESSING: Add samples but prefer recent data
                        let mut samples_added = 0;
                        
                        // If buffer is getting full, only add the most recent part of the packet
                        let samples_to_add = if buffer_usage_percent > 15.0 {
                            // When buffer > 15%, only take last 50% of packet (most recent audio)
                            let start_idx = samples.len() / 2;
                            &samples[start_idx..]
                        } else {
                            // Normal case: add entire packet
                            &samples
                        };
                        
                        for &sample in samples_to_add {
                            match producer.push(sample) {
                                Ok(_) => samples_added += 1,
                                Err(_) => {
                                    // Buffer full - this should not happen with our aggressive management
                                    eprintln!("CRITICAL: Buffer completely full despite aggressive management!");
                                    break;
                                }
                            }
                        }
                        
                        // Real-time diagnostic logging
                        if self.audio_packet_counter % 50 == 0 { // Every ~500ms
                            let estimated_latency_ms = (buffer_used_space * 1000) / 48000;
                            eprintln!("REALTIME: Pkt#{} | Buffer: {}% ({} samples, ~{}ms latency) | Added: {}/{}", 
                                      self.audio_packet_counter, 
                                      buffer_usage_percent as u32, 
                                      buffer_used_space,
                                      estimated_latency_ms,
                                      samples_added, 
                                      samples_to_add.len());
                        }
                        
                        // Update buffer metrics for GUI display  
                        self.buffer_usage = buffer_usage_percent;
                        self.estimated_latency_ms = (buffer_used_space * 1000) / 48000;
                    } else {
                        eprintln!("DEBUG: Received audio but no producer (call not started?)");
                    }
                },
                GuiUpdate::UdpAudioClientReady { client } => {
                    eprintln!("DEBUG: UDP audio client ready and connected");
                    self.udp_audio_client = Some(client);
                    // Initialize real-time buffer for UDP mode
                    self.real_time_buffer = pqc_chat::udp_audio::RealTimeAudioBuffer::new(150); // 150ms max age
                    self.add_status_message("🚀 UDP audio client connected - ultra-low latency mode!".to_string());
                },
            }
        }
    }

    fn add_status_message(&mut self, message: String) {
        self.status_messages.push((message, std::time::SystemTime::now()));
        // Keep only last 50 messages
        if self.status_messages.len() > 50 {
            self.status_messages.remove(0);
        }
    }

    fn send_command(&self, command: GuiCommand) {
        if let Some(sender) = &self.command_sender {
            let _ = sender.send(command);
        }
    }

    fn start_audio_call(&mut self) {
        log::info!("Starting audio call...");
        
        // Create audio manager
        let mut manager = match pqc_chat::audio::AudioManager::new() {
            Ok(m) => m,
            Err(e) => {
                self.add_status_message(format!("❌ Failed to create audio manager: {}", e));
                return;
            }
        };

        // Start playback first
        let producer = match manager.start_playback() {
            Ok(p) => p,
            Err(e) => {
                self.add_status_message(format!("❌ Failed to start playback: {}", e));
                return;
            }
        };
        self.audio_producer = Some(producer);

        // Initialize UDP audio client if using UDP mode
        if self.use_udp_audio {
            // Extract host and port from current connection
            if !self.server_host.is_empty() {
                let host = self.server_host.clone();
                let port: u16 = self.server_port.parse().unwrap_or(8443);
                let udp_port = port + 1; // UDP audio server is on port+1
                
                // Send command to initialize UDP client asynchronously
                eprintln!("DEBUG: Requesting UDP audio client initialization for {}:{}", host, udp_port);
                if let Some(ref sender) = self.command_sender {
                    let _ = sender.send(GuiCommand::InitializeUdpAudio { host, port: udp_port });
                }
            } else {
                self.add_status_message("❌ No server connection for UDP audio".to_string());
                return;
            }
        }

        // Start capture with callback - always use command sender for now
        let command_sender = self.command_sender.clone();
        let use_udp = self.use_udp_audio;
        let udp_client = self.udp_audio_client.clone();
        
        let capture_result = manager.start_capture(move |samples| {
            // Convert samples to bytes
            let bytes = pqc_chat::audio::samples_to_bytes(&samples);
            eprintln!("DEBUG: Captured {} samples -> {} bytes, UDP mode: {}", samples.len(), bytes.len(), use_udp);
            
            // Send through appropriate channel (UDP direct or TCP via command system)
            if use_udp {
                // Send directly via UDP client for ultra-low latency
                if let Some(client) = &udp_client {
                    // Use tokio to spawn async task for UDP sending
                    let client_clone = client.clone();
                    let bytes_clone = bytes.clone();
                    tokio::spawn(async move {
                        if let Err(e) = client_clone.send_audio_chunk(bytes_clone).await {
                            eprintln!("ERROR: Failed to send UDP audio data: {}", e);
                        }
                    });
                } else {
                    eprintln!("ERROR: UDP client not initialized but UDP mode enabled");
                }
            } else {
                // Send through TCP command system
                if let Some(sender) = &command_sender {
                    let _ = sender.send(GuiCommand::SendAudioData { data: bytes });
                }
            }
        });

        if let Err(e) = capture_result {
            self.add_status_message(format!("❌ Failed to start capture: {}", e));
            manager.stop_playback();
            self.audio_producer = None;
            return;
        }

        self.audio_manager = Some(Arc::new(Mutex::new(manager)));
        self.audio_call_active = true;
        self.add_status_message("🎤 Audio call started - speak now!".to_string());
        log::info!("Audio call started successfully");
    }

    fn stop_audio_call(&mut self) {
        log::info!("Stopping audio call...");
        
        // Reset all audio state
        self.audio_packet_counter = 0;
        self.last_buffer_reset = std::time::SystemTime::now();
        self.consecutive_high_buffer = 0;
        
        eprintln!("DEBUG: Resetting all audio state on stop");
        
        // Stop audio manager
        if let Some(manager_arc) = self.audio_manager.take() {
            if let Ok(mut manager) = manager_arc.lock() {
                manager.stop_all();
            }
        }
        
        // Clear producer reference
        self.audio_producer = None;
        self.audio_call_active = false;
        
        self.add_status_message("🔇 Audio call ended".to_string());
        log::info!("Audio call stopped");
    }

}

#[cfg(feature = "gui")]
impl eframe::App for EnhancedPqcChatApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Process updates from backend
        self.process_updates();

        // Request repaint for live updates
        ctx.request_repaint();

        // Top menu bar
        egui::TopBottomPanel::top("top_panel").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.heading("🔐 PQC Chat - Post-Quantum Secure");
                ui.separator();
                ui.label(&self.connection_status);
                ui.separator();
                
                let users_resp = ui.checkbox(&mut self.show_users_panel, "👥 Users");
                // Keep the floating window open state in sync with the checkbox
                if users_resp.changed() {
                    self.users_window_open = self.show_users_panel;
                }
                ui.checkbox(&mut self.show_rooms_panel, "🏠 Rooms");
                
                if self.is_connected {
                    ui.separator();
                    if ui.button("🔌 Disconnect").clicked() {
                        self.send_command(GuiCommand::Disconnect);
                    }
                }
            });
        });

        // Left panel - Connection and Rooms
        egui::SidePanel::left("left_panel")
            .resizable(true)
            .default_width(300.0)
            .show(ctx, |ui| {
                if !self.is_connected {
                    ui.heading("Connection");
                    ui.separator();
                    
                    ui.label("Server Host:");
                    ui.text_edit_singleline(&mut self.server_host);
                    
                    ui.label("Port:");
                    ui.text_edit_singleline(&mut self.server_port);
                    
                    ui.label("Username:");
                    ui.text_edit_singleline(&mut self.username);
                    
                    ui.separator();
                    
                    if ui.button("🔌 Connect").clicked() {
                        if let Ok(port) = self.server_port.parse() {
                            self.send_command(GuiCommand::Connect {
                                host: self.server_host.clone(),
                                port,
                                username: self.username.clone(),
                            });
                        }
                    }
                } else if self.show_rooms_panel {
                    ui.heading("Rooms");
                    ui.separator();
                    
                    // Current room status
                    if let Some(room) = &self.current_room {
                        ui.group(|ui| {
                            ui.label("📍 Current Room:");
                            ui.strong(&room.name);
                            ui.label(format!("👥 {} / {} participants (GUI sees: {})", room.participants, room.max_participants, self.room_participants.len()));
                            if ui.button("👋 Leave Room").clicked() {
                                self.send_command(GuiCommand::LeaveRoom);
                            }
                            if ui.button("🔄 Debug Refresh").clicked() {
                                self.send_command(GuiCommand::ListRooms);
                            }
                        });
                        ui.separator();
                    }
                    
                    // Room list
                    ui.horizontal(|ui| {
                        ui.label("🏠 Available Rooms:");
                        if ui.button("🔄").clicked() {
                            self.send_command(GuiCommand::ListRooms);
                        }
                    });
                    
                    egui::ScrollArea::vertical()
                        .max_height(200.0)
                        .show(ui, |ui| {
                            for (idx, room) in self.rooms.iter().enumerate() {
                                let is_selected = self.selected_room_idx == Some(idx);
                                let response = ui.selectable_label(is_selected, format!(
                                    "🏠 {} ({}/{}{})",
                                    room.name,
                                    room.participants,
                                    room.max_participants,
                                    if room.is_locked { " 🔒" } else { "" }
                                ));
                                
                                if response.clicked() {
                                    self.selected_room_idx = Some(idx);
                                }
                                
                                if response.double_clicked() {
                                    self.send_command(GuiCommand::JoinRoom {
                                        room_id: room.id.clone(),
                                    });
                                }
                            }
                        });
                    
                    if let Some(idx) = self.selected_room_idx {
                        if idx < self.rooms.len() && ui.button("🚪 Join Room").clicked() {
                            self.send_command(GuiCommand::JoinRoom {
                                room_id: self.rooms[idx].id.clone(),
                            });
                        }
                    }
                    
                    ui.separator();
                    
                    // Create room
                    ui.label("Create New Room:");
                    ui.text_edit_singleline(&mut self.new_room_name);
                    
                    if ui.button("➕ Create Room").clicked() && !self.new_room_name.is_empty() {
                        self.send_command(GuiCommand::CreateRoom {
                            name: self.new_room_name.clone(),
                            max_participants: 10,
                        });
                        self.new_room_name.clear();
                    }
                }
            });

        // Right panel - Connected Users
        // Hide the server-wide users panel when we're inside a room (to avoid layout issues)
        if self.show_users_panel && self.current_room.is_none() {
            egui::SidePanel::right("users_panel")
                .resizable(true)
                .default_width(250.0)
                .show(ctx, |ui| {
                    ui.horizontal(|ui| {
                        ui.heading("👥 Connected Users (Server-wide)");
                        if ui.button("🔄").on_hover_text("Refresh user list").clicked() {
                            self.send_command(GuiCommand::ListServerUsers);
                        }
                    });
                    ui.separator();
                    
                    ui.label("All users connected to the server:");
                    ui.label(format!("Currently showing: {} users", self.connected_users.len()));
                    ui.separator();
                    
                    egui::ScrollArea::vertical()
                        .auto_shrink([false; 2])
                        .show(ui, |ui| {
                            if self.connected_users.is_empty() {
                                ui.vertical_centered(|ui| {
                                    ui.label("📭 No users found");
                                    ui.small("Click refresh or check server connection");
                                });
                            } else {
                                for (user_id, user) in &self.connected_users {
                                    ui.group(|ui| {
                                        ui.horizontal(|ui| {
                                            let audio_icon = if user.audio_enabled { "🎤" } else { "🔇" };
                                            let video_icon = if user.video_enabled { "📹" } else { "📺" };
                                            
                                            ui.label(format!("{} {}", audio_icon, video_icon));
                                            
                                            if user.username == self.username {
                                                ui.strong(&user.username);
                                                ui.label("(You)");
                                            } else {
                                                ui.label(&user.username);
                                            }
                                        });
                                        
                                        if let Some(room) = &user.in_room {
                                            ui.label(format!("🏠 In room: {}", room));
                                        } else {
                                            ui.label("🏠 In lobby");
                                        }
                                        
                                        // Show connection time
                                        if let Ok(duration) = user.connected_at.elapsed() {
                                            let mins = duration.as_secs() / 60;
                                            if mins > 0 {
                                                ui.label(format!("⏱️ Online {}m", mins));
                                            } else {
                                                ui.label("⏱️ Just joined");
                                            }
                                        } else {
                                            ui.label("⏱️ Online");
                                        }
                                        
                                        ui.small(format!("ID: {}", user_id));
                                    });
                                    ui.separator();
                                }
                            }
                        });
                });
        }

        // Chat input bottom panel - only show when in a room
        if self.current_room.is_some() {
            egui::TopBottomPanel::bottom("chat_input_panel")
                .show(ctx, |ui| {
                    ui.horizontal(|ui| {
                        let response = ui.text_edit_singleline(&mut self.message_input);

                        let send_clicked = ui.button("📤 Send").clicked();
                        let enter_pressed = response.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter));

                        if (send_clicked || enter_pressed) && !self.message_input.trim().is_empty() {
                            let content = self.message_input.trim().to_string();

                            // Optimistic update: show your own message immediately for better UX
                            // The deduplication logic will prevent it from showing twice when broadcast returns
                            if let Some(ref room) = self.current_room {
                                let room_id = room.id.clone();
                                let chat_history = self.room_chat_history.entry(room_id).or_insert_with(Vec::new);
                                
                                chat_history.push(ChatMessage {
                                    sender_id: "optimistic".to_string(),
                                    sender_username: self.username.clone(),
                                    content: content.clone(),
                                    timestamp: std::time::SystemTime::now(),
                                });
                                
                                if chat_history.len() > 100 {
                                    chat_history.remove(0);
                                }
                            }

                            // Send message - server will broadcast to everyone (including us)
                            self.send_command(GuiCommand::SendMessage { content });
                            self.message_input.clear();
                            response.request_focus();
                        }
                    });
                });
        }

        // Central panel - Chat and room controls
        egui::CentralPanel::default().show(ctx, |ui| {
            if self.is_connected {
                if let Some(room) = self.current_room.clone() {
                    // Room header with controls
                    ui.horizontal(|ui| {
                        ui.heading(format!("🏠 {}", room.name));
                        ui.separator();
                        
                        // Media controls
                        if self.audio_enabled {
                            if ui.button("🎤").on_hover_text("Turn audio OFF").clicked() {
                                self.audio_enabled = false;
                                self.send_command(GuiCommand::ToggleAudio { enabled: false });
                            }
                        } else {
                            if ui.button("🔇").on_hover_text("Turn audio ON").clicked() {
                                self.audio_enabled = true;
                                self.send_command(GuiCommand::ToggleAudio { enabled: true });
                            }
                        }
                        
                        if self.video_enabled {
                            if ui.button("📹").on_hover_text("Turn video OFF").clicked() {
                                self.video_enabled = false;
                                self.send_command(GuiCommand::ToggleVideo { enabled: false });
                            }
                        } else {
                            if ui.button("📺").on_hover_text("Turn video ON").clicked() {
                                self.video_enabled = true;
                                self.send_command(GuiCommand::ToggleVideo { enabled: true });
                            }
                        }
                        
                        ui.separator();
                        
                        // Audio transport mode toggle
                        ui.horizontal(|ui| {
                            ui.label("Audio Mode:");
                            if ui.selectable_label(self.use_udp_audio, "🚀 UDP (Ultra-Low Latency)").clicked() {
                                self.use_udp_audio = true;
                                self.add_status_message("Switched to UDP audio mode".to_string());
                            }
                            if ui.selectable_label(!self.use_udp_audio, "📡 TCP (Reliable)").clicked() {
                                self.use_udp_audio = false;
                                self.add_status_message("Switched to TCP audio mode".to_string());
                            }
                        });
                        
                        ui.separator();
                        
                        // Audio call control
                        if self.audio_call_active {
                            if ui.button("📞 End Call").on_hover_text("Stop audio call").clicked() {
                                self.audio_call_active = false;
                                self.stop_audio_call();
                            }
                        } else {
                            if ui.button("📞 Start Call").on_hover_text("Start audio call with room participants").clicked() {
                                self.audio_call_active = true;
                                self.start_audio_call();
                            }
                        }
                        
                        ui.separator();
                        ui.label(format!("👥 {} participants", self.room_participants.len()));
                        
                        // REAL-TIME BUFFER MONITORING (when in audio call)
                        if self.audio_call_active {
                            ui.separator();
                            let buffer_color = if self.buffer_usage > 50.0 {
                                egui::Color32::RED
                            } else if self.buffer_usage > 25.0 {
                                egui::Color32::YELLOW
                            } else {
                                egui::Color32::GREEN
                            };
                            
                            ui.colored_label(buffer_color, 
                                format!("🔊 Buffer: {:.0}% (~{}ms latency)", 
                                       self.buffer_usage, self.estimated_latency_ms));
                            
                            if self.consecutive_high_buffer > 0 {
                                ui.colored_label(egui::Color32::from_rgb(255, 165, 0),
                                    format!("⚠️ High buffer events: {}", self.consecutive_high_buffer));
                            }
                        }
                    });
                    
                    ui.separator();

                    // Chat area - full width, scrollable, extends from header to input bar
                    ui.vertical(|ui| {
                        let chat_max_h = ui.available_height();
                        ui.set_min_height(chat_max_h);
                        
                        egui::ScrollArea::vertical()
                            .id_source("chat_scroll_area")
                            .max_height(chat_max_h)
                            .stick_to_bottom(true)
                            .show(ui, |ui| {
                                // Get messages for current room
                                let messages = if let Some(ref room) = self.current_room {
                                    self.room_chat_history.get(&room.id)
                                } else {
                                    None
                                };
                                
                                if let Some(msgs) = messages {
                                    if msgs.is_empty() {
                                        ui.vertical_centered(|ui| {
                                            ui.label("🗨️ No messages yet");
                                            ui.small("Start the conversation!");
                                        });
                                    } else {
                                        for msg in msgs {
                                            ui.group(|ui| {
                                                ui.horizontal(|ui| {
                                                    if msg.sender_username == self.username {
                                                        ui.strong("You");
                                                    } else {
                                                        ui.label(&msg.sender_username);
                                                    }
                                                    ui.small(format_time(msg.timestamp));
                                                });
                                                ui.label(&msg.content);
                                            });
                                            ui.separator();
                                        }
                                    }
                                } else {
                                    ui.vertical_centered(|ui| {
                                        ui.label("🗨️ No messages yet");
                                        ui.small("Start the conversation!");
                                    });
                                }
                            });
                    });

                } else {
                    ui.vertical_centered(|ui| {
                        ui.heading("Welcome to PQC Chat!");
                        ui.label("🔐 Post-Quantum Secure Video Chat");
                        ui.separator();
                        ui.label("Select a room from the left panel or create a new one to start chatting.");
                        ui.separator();
                        
                        // Status messages in lobby
                        ui.heading("📨 Recent Activity");
                        egui::ScrollArea::vertical()
                            .max_height(200.0)
                            .show(ui, |ui| {
                                if self.status_messages.is_empty() {
                                    ui.label("No recent activity");
                                } else {
                                    for (message, _timestamp) in self.status_messages.iter().rev().take(10) {
                                        ui.label(message);
                                    }
                                }
                            });
                    });
                }
            } else {
                ui.vertical_centered(|ui| {
                    ui.heading("🔐 PQC Chat");
                    ui.label("Post-Quantum Secure Video Chat System");
                    ui.separator();
                    ui.label("Enter your connection details in the left panel to get started.");
                });
            }
        });

        // Floating users window when in a room (controlled by the Users checkbox)
        if self.show_users_panel && self.current_room.is_some() && self.users_window_open {
            let mut users_open = self.users_window_open;
            egui::Window::new("👥 Connected Users (Server-wide)")
                .open(&mut users_open)
                .resizable(true)
                .default_width(320.0)
                .default_height(400.0)
                .collapsible(true)
                .show(ctx, |ui| {
                    ui.horizontal(|ui| {
                        ui.heading("👥 Connected Users (Server-wide)");
                        if ui.button("🔄").on_hover_text("Refresh user list").clicked() {
                            self.send_command(GuiCommand::ListServerUsers);
                        }
                    });
                    ui.separator();

                    ui.label("All users connected to the server:");
                    ui.label(format!("Currently showing: {} users", self.connected_users.len()));
                    ui.separator();

                    egui::ScrollArea::vertical()
                        .auto_shrink([false; 2])
                        .show(ui, |ui| {
                            if self.connected_users.is_empty() {
                                ui.vertical_centered(|ui| {
                                    ui.label("📭 No users found");
                                    ui.small("Click refresh or check server connection");
                                });
                            } else {
                                for (user_id, user) in &self.connected_users {
                                    ui.group(|ui| {
                                        ui.horizontal(|ui| {
                                            let audio_icon = if user.audio_enabled { "🎤" } else { "🔇" };
                                            let video_icon = if user.video_enabled { "📹" } else { "📺" };

                                            ui.label(format!("{} {}", audio_icon, video_icon));

                                            if user.username == self.username {
                                                ui.strong(&user.username);
                                                ui.label("(You)");
                                            } else {
                                                ui.label(&user.username);
                                            }
                                        });

                                        if let Some(room) = &user.in_room {
                                            ui.label(format!("🏠 In room: {}", room));
                                        } else {
                                            ui.label("🏠 In lobby");
                                        }

                                        if let Ok(duration) = user.connected_at.elapsed() {
                                            let mins = duration.as_secs() / 60;
                                            if mins > 0 {
                                                ui.label(format!("⏱️ Online {}m", mins));
                                            } else {
                                                ui.label("⏱️ Just joined");
                                            }
                                        } else {
                                            ui.label("⏱️ Online");
                                        }

                                        ui.small(format!("ID: {}", user_id));
                                    });
                                    ui.separator();
                                }
                            }
                        });
                });
            // commit any user-closed change back into the app state
            self.users_window_open = users_open;
        }
    }
}

#[cfg(feature = "gui")]
async fn communication_task(
    mut command_receiver: mpsc::UnboundedReceiver<GuiCommand>,
    update_sender: mpsc::UnboundedSender<GuiUpdate>,
) {
    use tokio::net::TcpStream;
    use std::sync::Arc;
    use tokio::sync::Mutex;
    
    let mut connection: Option<Arc<Mutex<tokio_rustls::client::TlsStream<TcpStream>>>> = None;
    let mut _participant_id: Option<String> = None;
    let mut current_username: Option<String> = None;
    
    loop {
        if let Some(ref conn_arc) = connection.clone() {
            // When connected, listen for both commands and incoming messages
            let conn_arc_cmd = conn_arc.clone();
            let conn_arc_recv = conn_arc.clone();
            
            tokio::select! {
                Some(command) = command_receiver.recv() => {
                    let mut conn = conn_arc_cmd.lock().await;
                    let username = current_username.as_deref().unwrap_or("User");
                    match command {
                        GuiCommand::Disconnect => {
                            connection = None;
                            _participant_id = None;
                            current_username = None;
                            let _ = update_sender.send(GuiUpdate::Disconnected);
                        },
                        _ => {
                            let _ = handle_command(&mut *conn, command, &update_sender, username).await;
                        }
                    }
                }
                result = async {
                    let mut conn = conn_arc_recv.lock().await;
                    receive_message(&mut *conn).await
                } => {
                    match result {
                        Ok(msg) => {
                            eprintln!("DEBUG: Received message in main loop: {:?}", msg);
                            process_server_message(msg, &update_sender).await;
                        }
                        Err(e) => {
                            eprintln!("DEBUG: Connection error in main loop: {:?}", e);
                            // Connection closed
                            connection = None;
                            let _ = update_sender.send(GuiUpdate::Disconnected);
                        }
                    }
                }
            }
        } else {
            // Not connected, just wait for connect command
            if let Some(command) = command_receiver.recv().await {
                if let GuiCommand::Connect { host, port, username } = command {
                    match connect_to_server(&host, port, &username, &update_sender).await {
                        Ok((stream, pid)) => {
                            connection = Some(Arc::new(Mutex::new(stream)));
                            _participant_id = Some(pid.clone());
                            current_username = Some(username.clone());
                            let _ = update_sender.send(GuiUpdate::Connected { participant_id: pid.clone() });
                            
                            // Request initial room list
                            if let Some(ref conn_arc) = connection {
                                let mut conn = conn_arc.lock().await;
                                let _ = send_message(&mut *conn, &SignalingMessage::ListRooms).await;
                            }
                        },
                        Err(e) => {
                            let _ = update_sender.send(GuiUpdate::ConnectionError { 
                                error: e.to_string() 
                            });
                        }
                    }
                }
            }
        }
    }
}

#[cfg(feature = "gui")]
async fn connect_to_server(
    host: &str,
    port: u16,
    username: &str,
    _update_sender: &mpsc::UnboundedSender<GuiUpdate>,
) -> Result<(tokio_rustls::client::TlsStream<tokio::net::TcpStream>, String), Box<dyn std::error::Error + Send + Sync>> {
    use tokio::net::TcpStream;
    use tokio_rustls::rustls::{self, pki_types::ServerName};
    use tokio_rustls::TlsConnector;
    use std::sync::Arc;
    
    // Create TLS config that accepts self-signed certificates (for development)
    let tls_config = rustls::ClientConfig::builder()
        .dangerous()
        .with_custom_certificate_verifier(Arc::new(NoVerifier))
        .with_no_client_auth();
    
    let connector = TlsConnector::from(Arc::new(tls_config));
    
    // Connect to server
    let addr = format!("{}:{}", host, port);
    let stream = TcpStream::connect(&addr).await?;
    let server_name = ServerName::try_from(host.to_string())?;
    let mut tls_stream = connector.connect(server_name, stream).await?;
    
    // Perform Kyber key exchange
    let kyber = KyberKeyExchange::new();
    let key_init = SignalingMessage::KeyExchangeInit {
        public_key: kyber.public_key_bytes(),
    };
    send_message(&mut tls_stream, &key_init).await?;
    
    let response = receive_message(&mut tls_stream).await?;
    if let SignalingMessage::KeyExchangeResponse { ciphertext } = response {
        kyber.decapsulate(&ciphertext)?;
    } else {
        return Err("Key exchange failed".into());
    }
    
    // Login
    let login = SignalingMessage::Login {
        username: username.to_string(),
    };
    send_message(&mut tls_stream, &login).await?;
    
    let response = receive_message(&mut tls_stream).await?;
    if let SignalingMessage::LoginResponse { success, participant_id, .. } = response {
        if success {
            if let Some(pid) = participant_id {
                return Ok((tls_stream, pid));
            }
        }
    }
    
    Err("Login failed".into())
}

#[cfg(feature = "gui")]
async fn handle_command(
    stream: &mut tokio_rustls::client::TlsStream<tokio::net::TcpStream>,
    command: GuiCommand,
    update_sender: &mpsc::UnboundedSender<GuiUpdate>,
    username: &str,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let message = match command {
        GuiCommand::ListRooms => SignalingMessage::ListRooms,
        GuiCommand::CreateRoom { name, max_participants } => SignalingMessage::CreateRoom {
            name,
            max_participants: Some(max_participants),
        },
        GuiCommand::JoinRoom { room_id } => SignalingMessage::JoinRoom {
            room_id,
            username: username.to_string(),
        },
        GuiCommand::LeaveRoom => SignalingMessage::LeaveRoom,
        GuiCommand::ToggleAudio { enabled } => SignalingMessage::ToggleAudio { enabled },
        GuiCommand::ToggleVideo { enabled } => SignalingMessage::ToggleVideo { enabled },
        GuiCommand::ListServerUsers => SignalingMessage::ListServerUsers,
        GuiCommand::SendMessage { content } => {
            // Send chat message
            let msg = SignalingMessage::SendMessage { content: content.clone() };
            eprintln!("DEBUG: Sending message to server: {}", content);
            eprintln!("DEBUG: Message JSON: {}", serde_json::to_string(&msg).unwrap_or_else(|_| "ERROR".to_string()));
            send_message(stream, &msg).await?;
            // Read and discard the acknowledgment response
            // The actual message will come via broadcast to all participants
            let ack = receive_message(stream).await?;
            eprintln!("DEBUG: Received acknowledgment: {:?}", ack);
            return Ok(());
        },
        GuiCommand::SendAudioData { data } => {
            // Send audio data through signaling
            eprintln!("DEBUG: Sending {} bytes of audio data via TCP", data.len());
            let msg = SignalingMessage::AudioData { data };
            send_message(stream, &msg).await?;
            // Audio data doesn't need response
            return Ok(());
        },
        GuiCommand::SendUdpAudioData { data } => {
            eprintln!("DEBUG: Sending {} bytes of audio data via UDP (bypassing TCP)", data.len());
            // UDP audio data is handled directly by the UDP client - no TCP signaling needed
            // The UDP client should be initialized and sending data directly to server
            return Ok(());
        },
        GuiCommand::StartAudioCall | GuiCommand::StopAudioCall => {
            // These are handled locally in the GUI
            return Ok(());
        },
        GuiCommand::InitializeUdpAudio { host, port } => {
            eprintln!("DEBUG: Initializing UDP audio client for {}:{}", host, port);
            let server_addr = format!("{}:{}", host, port).parse::<std::net::SocketAddr>();
            match server_addr {
                Ok(addr) => {
                    // Generate a session ID based on username (we'll use a simple UUID for now)
                    let session_id = uuid::Uuid::new_v4().to_string();
                    match pqc_chat::udp_audio::UdpAudioClient::new(addr, session_id).await {
                        Ok(udp_client) => {
                            eprintln!("DEBUG: UDP audio client successfully connected to {}:{}", host, port);
                            let _ = update_sender.send(GuiUpdate::UdpAudioClientReady { client: udp_client });
                        }
                        Err(e) => {
                            eprintln!("ERROR: Failed to initialize UDP audio client: {}", e);
                            let _ = update_sender.send(GuiUpdate::ConnectionError { 
                                error: format!("UDP audio client failed: {}", e) 
                            });
                        }
                    }
                }
                Err(e) => {
                    eprintln!("ERROR: Invalid server address {}:{}: {}", host, port, e);
                    let _ = update_sender.send(GuiUpdate::ConnectionError { 
                        error: format!("Invalid server address: {}", e) 
                    });
                }
            }
            return Ok(());
        },
        _ => return Ok(()),
    };
    
    send_message(stream, &message).await?;
    let response = receive_message(stream).await?;
    
    // Process response
    match response {
        SignalingMessage::RoomList { rooms } => {
            let _ = update_sender.send(GuiUpdate::RoomList { rooms });
        },
        SignalingMessage::RoomJoined { success, room_name, participants, .. } => {
            if success {
                if let (Some(name), Some(parts)) = (room_name, participants) {
                    let room = RoomInfo {
                        id: "temp".to_string(), // TODO: Get actual room ID
                        name,
                        participants: parts.len() as u32,
                        max_participants: 10,
                        is_locked: false,
                    };
                    let _ = update_sender.send(GuiUpdate::RoomJoined { room, participants: parts });
                }
            }
        },
        SignalingMessage::RoomLeft { success, .. } => {
            if success {
                let _ = update_sender.send(GuiUpdate::RoomLeft);
            }
        },
        SignalingMessage::ParticipantJoined { participant_id, username } => {
            let participant = ParticipantInfo {
                id: participant_id.clone(),
                username: username.clone(),
                audio_enabled: true,
                video_enabled: false,
            };
            let _ = update_sender.send(GuiUpdate::ParticipantJoined { participant });
            
            // Also update server-wide connected users with this new user
            let user = ConnectedUser {
                id: participant_id.clone(),
                username: username.clone(),
                connected_at: std::time::SystemTime::now(),
                in_room: Some("Current Room".to_string()), // TODO: Get actual room name
                audio_enabled: true,
                video_enabled: false,
            };
            let _ = update_sender.send(GuiUpdate::ServerUserConnected { user });
        },
        SignalingMessage::ParticipantLeft { participant_id } => {
            let _ = update_sender.send(GuiUpdate::ParticipantLeft { participant_id });
            // Note: Don't remove from server users - they may still be connected to server
        },
        SignalingMessage::ServerUserList { users } => {
            let connected_users = users.into_iter().map(|server_user| {
                ConnectedUser {
                    id: server_user.id,
                    username: server_user.username,
                    connected_at: std::time::UNIX_EPOCH + std::time::Duration::from_secs(server_user.connected_at),
                    in_room: server_user.current_room,
                    audio_enabled: server_user.audio_enabled,
                    video_enabled: server_user.video_enabled,
                }
            }).collect();
            let _ = update_sender.send(GuiUpdate::ServerUserList { users: connected_users });
        },
        SignalingMessage::MessageReceived { sender_id, sender_username, content, timestamp } => {
            let chat_message = ChatMessage {
                sender_id,
                sender_username,
                content,
                timestamp: std::time::UNIX_EPOCH + std::time::Duration::from_secs(timestamp),
            };
            let _ = update_sender.send(GuiUpdate::ChatMessageReceived { message: chat_message });
        },
        SignalingMessage::Error { message } => {
            let _ = update_sender.send(GuiUpdate::StatusMessage { message });
        },
        _ => {
            // Handle other message types
        }
    }
    
    Ok(())
}

#[cfg(feature = "gui")]
async fn process_server_message(
    message: SignalingMessage,
    update_sender: &mpsc::UnboundedSender<GuiUpdate>,
) {
    eprintln!("DEBUG: process_server_message called with: {:?}", message);
    // Handle unsolicited broadcasts from the server (messages, participant joins/leaves, etc.)
    match message {
        SignalingMessage::MessageReceived { sender_id, sender_username, content, timestamp } => {
            eprintln!("DEBUG: Processing MessageReceived from {} ({}): {}", sender_username, sender_id, content);
            let chat_message = ChatMessage {
                sender_id: sender_id.clone(),
                sender_username: sender_username.clone(),
                content: content.clone(),
                timestamp: std::time::UNIX_EPOCH + std::time::Duration::from_secs(timestamp),
            };
            eprintln!("DEBUG: Sending GuiUpdate::ChatMessageReceived");
            let _ = update_sender.send(GuiUpdate::ChatMessageReceived { message: chat_message });
        },
        SignalingMessage::ParticipantJoined { participant_id, username } => {
            let participant = ParticipantInfo {
                id: participant_id.clone(),
                username: username.clone(),
                audio_enabled: true,
                video_enabled: false,
            };
            let _ = update_sender.send(GuiUpdate::ParticipantJoined { participant });
        },
        SignalingMessage::ParticipantLeft { participant_id } => {
            let _ = update_sender.send(GuiUpdate::ParticipantLeft { participant_id });
        },
        SignalingMessage::AudioDataReceived { sender_id, data } => {
            let _ = update_sender.send(GuiUpdate::AudioDataReceived { sender_id, data });
        },
        _ => {
            // Ignore other message types in broadcasts
        }
    }
}

#[cfg(feature = "gui")]
async fn send_message(
    stream: &mut tokio_rustls::client::TlsStream<tokio::net::TcpStream>,
    message: &SignalingMessage,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let data = message.to_framed()?;
    stream.write_all(&data).await?;
    Ok(())
}

#[cfg(feature = "gui")]
async fn receive_message(
    stream: &mut tokio_rustls::client::TlsStream<tokio::net::TcpStream>,
) -> Result<SignalingMessage, Box<dyn std::error::Error + Send + Sync>> {
    let mut len_buf = [0u8; 4];
    stream.read_exact(&mut len_buf).await?;
    let msg_len = u32::from_be_bytes(len_buf) as usize;

    let mut msg_buf = vec![0u8; msg_len];
    stream.read_exact(&mut msg_buf).await?;

    Ok(SignalingMessage::from_bytes(&msg_buf)?)
}

#[cfg(feature = "gui")]
#[derive(Debug)]
struct NoVerifier;

#[cfg(feature = "gui")]
impl rustls::client::danger::ServerCertVerifier for NoVerifier {
    fn verify_server_cert(
        &self,
        _end_entity: &rustls::pki_types::CertificateDer<'_>,
        _intermediates: &[rustls::pki_types::CertificateDer<'_>],
        _server_name: &rustls::pki_types::ServerName<'_>,
        _ocsp_response: &[u8],
        _now: rustls::pki_types::UnixTime,
    ) -> Result<rustls::client::danger::ServerCertVerified, rustls::Error> {
        Ok(rustls::client::danger::ServerCertVerified::assertion())
    }

    fn verify_tls12_signature(
        &self,
        _message: &[u8],
        _cert: &rustls::pki_types::CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn verify_tls13_signature(
        &self,
        _message: &[u8],
        _cert: &rustls::pki_types::CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        vec![
            rustls::SignatureScheme::RSA_PKCS1_SHA256,
            rustls::SignatureScheme::RSA_PKCS1_SHA384,
            rustls::SignatureScheme::RSA_PKCS1_SHA512,
            rustls::SignatureScheme::ECDSA_NISTP256_SHA256,
            rustls::SignatureScheme::ECDSA_NISTP384_SHA384,
            rustls::SignatureScheme::ECDSA_NISTP521_SHA512,
            rustls::SignatureScheme::RSA_PSS_SHA256,
            rustls::SignatureScheme::RSA_PSS_SHA384,
            rustls::SignatureScheme::RSA_PSS_SHA512,
            rustls::SignatureScheme::ED25519,
        ]
    }
}