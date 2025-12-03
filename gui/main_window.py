"""
PQC Chat GUI Application

Provides a simple tkinter-based GUI for the PQC chat client with
controls for connecting, joining rooms, and managing audio/video.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.client_engine import PQCChatClient, ClientConfig

logger = logging.getLogger(__name__)


class PQCChatGUI:
    """
    Main GUI application for PQC Chat.
    
    Provides a simple interface with controls for:
    - Connecting to server
    - Browsing and joining rooms
    - Creating new rooms
    - Toggling audio/video
    - Leaving rooms
    - Disconnecting
    """
    
    def __init__(self, root: tk.Tk):
        """
        Initialize the GUI application.
        
        Args:
            root: The tkinter root window.
        """
        self.root = root
        self.root.title("PQC Chat - Post-Quantum Secure")
        self.root.geometry("800x600")
        self.root.minsize(640, 480)
        
        # Client instance
        self._client: PQCChatClient = None
        self._config: ClientConfig = None
        
        # State
        self._connected = False
        self._in_room = False
        self._audio_enabled = True
        self._video_enabled = True
        
        # Build the UI
        self._build_ui()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
    def _build_ui(self):
        """Build the user interface."""
        # Create main container
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create sections
        self._build_connection_section()
        self._build_room_section()
        self._build_controls_section()
        self._build_participants_section()
        self._build_status_section()
        
        # Update UI state
        self._update_ui_state()
        
    def _build_connection_section(self):
        """Build the connection controls section."""
        frame = ttk.LabelFrame(self.main_frame, text="Connection", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # Server address
        server_frame = ttk.Frame(frame)
        server_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(server_frame, text="Server:").pack(side=tk.LEFT)
        self.server_entry = ttk.Entry(server_frame, width=30)
        self.server_entry.insert(0, "127.0.0.1")
        self.server_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(server_frame, text="Port:").pack(side=tk.LEFT)
        self.port_entry = ttk.Entry(server_frame, width=8)
        self.port_entry.insert(0, "8443")
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        # Username
        user_frame = ttk.Frame(frame)
        user_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(user_frame, text="Username:").pack(side=tk.LEFT)
        self.username_entry = ttk.Entry(user_frame, width=20)
        self.username_entry.insert(0, "User")
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        # Connect/Disconnect buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        
        self.connect_btn = ttk.Button(
            btn_frame, text="Connect", command=self._on_connect
        )
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.disconnect_btn = ttk.Button(
            btn_frame, text="Disconnect", command=self._on_disconnect
        )
        self.disconnect_btn.pack(side=tk.LEFT)
        
    def _build_room_section(self):
        """Build the room management section."""
        frame = ttk.LabelFrame(self.main_frame, text="Rooms", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Room list
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Treeview for rooms
        columns = ("name", "participants", "status")
        self.room_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=6)
        self.room_tree.heading("name", text="Room Name")
        self.room_tree.heading("participants", text="Participants")
        self.room_tree.heading("status", text="Status")
        self.room_tree.column("name", width=200)
        self.room_tree.column("participants", width=100)
        self.room_tree.column("status", width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.room_tree.yview)
        self.room_tree.configure(yscrollcommand=scrollbar.set)
        
        self.room_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Room buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        
        self.refresh_btn = ttk.Button(
            btn_frame, text="Refresh", command=self._on_refresh_rooms
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.create_room_btn = ttk.Button(
            btn_frame, text="Create Room", command=self._on_create_room
        )
        self.create_room_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.join_btn = ttk.Button(
            btn_frame, text="Join Room", command=self._on_join_room
        )
        self.join_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.leave_btn = ttk.Button(
            btn_frame, text="Leave Room", command=self._on_leave_room
        )
        self.leave_btn.pack(side=tk.LEFT)
        
    def _build_controls_section(self):
        """Build the audio/video control section."""
        frame = ttk.LabelFrame(self.main_frame, text="Media Controls", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # Audio control
        self.audio_var = tk.BooleanVar(value=True)
        self.audio_check = ttk.Checkbutton(
            frame, text="Audio Enabled", variable=self.audio_var,
            command=self._on_audio_toggle
        )
        self.audio_check.pack(side=tk.LEFT, padx=(0, 20))
        
        # Video control
        self.video_var = tk.BooleanVar(value=True)
        self.video_check = ttk.Checkbutton(
            frame, text="Video Enabled", variable=self.video_var,
            command=self._on_video_toggle
        )
        self.video_check.pack(side=tk.LEFT)
        
    def _build_participants_section(self):
        """Build the participants list section."""
        frame = ttk.LabelFrame(self.main_frame, text="Participants", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # Participant list
        self.participants_listbox = tk.Listbox(frame, height=4)
        self.participants_listbox.pack(fill=tk.X)
        
    def _build_status_section(self):
        """Build the status bar section."""
        frame = ttk.Frame(self.main_frame)
        frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(frame, text="Disconnected")
        self.status_label.pack(side=tk.LEFT)
        
        self.room_label = ttk.Label(frame, text="")
        self.room_label.pack(side=tk.RIGHT)
        
    def _update_ui_state(self):
        """Update UI elements based on current state."""
        # Connection controls
        self.server_entry.configure(state=tk.NORMAL if not self._connected else tk.DISABLED)
        self.port_entry.configure(state=tk.NORMAL if not self._connected else tk.DISABLED)
        self.username_entry.configure(state=tk.NORMAL if not self._connected else tk.DISABLED)
        self.connect_btn.configure(state=tk.NORMAL if not self._connected else tk.DISABLED)
        self.disconnect_btn.configure(state=tk.NORMAL if self._connected else tk.DISABLED)
        
        # Room controls
        self.refresh_btn.configure(state=tk.NORMAL if self._connected else tk.DISABLED)
        self.create_room_btn.configure(state=tk.NORMAL if self._connected and not self._in_room else tk.DISABLED)
        self.join_btn.configure(state=tk.NORMAL if self._connected and not self._in_room else tk.DISABLED)
        self.leave_btn.configure(state=tk.NORMAL if self._in_room else tk.DISABLED)
        
        # Media controls
        self.audio_check.configure(state=tk.NORMAL if self._in_room else tk.DISABLED)
        self.video_check.configure(state=tk.NORMAL if self._in_room else tk.DISABLED)
        
        # Status
        if self._connected:
            if self._in_room and self._client:
                self.status_label.configure(text=f"Connected as {self._client.username}")
                self.room_label.configure(text=f"Room: {self._client.current_room_name}")
            else:
                self.status_label.configure(text=f"Connected as {self._client.username if self._client else 'Unknown'}")
                self.room_label.configure(text="")
        else:
            self.status_label.configure(text="Disconnected")
            self.room_label.configure(text="")
            
    def _on_connect(self):
        """Handle connect button click."""
        server = self.server_entry.get().strip()
        port_str = self.port_entry.get().strip()
        username = self.username_entry.get().strip()
        
        if not server:
            messagebox.showerror("Error", "Please enter a server address")
            return
            
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return
            
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return
            
        # Create client configuration
        self._config = ClientConfig(
            server_host=server,
            signaling_port=port
        )
        
        # Create and connect client
        self._client = PQCChatClient(self._config)
        
        # Set up callbacks
        self._client.set_participant_joined_callback(self._on_participant_joined)
        self._client.set_participant_left_callback(self._on_participant_left)
        self._client.set_disconnected_callback(self._on_client_disconnected)
        
        # Connect in background thread
        def connect_task():
            try:
                if self._client.connect(username):
                    self.root.after(0, self._connection_success)
                else:
                    self.root.after(0, lambda: self._connection_failed("Connection failed"))
            except Exception as e:
                self.root.after(0, lambda: self._connection_failed(str(e)))
                
        threading.Thread(target=connect_task, daemon=True).start()
        
        # Show connecting state
        self.status_label.configure(text="Connecting...")
        self.connect_btn.configure(state=tk.DISABLED)
        
    def _connection_success(self):
        """Handle successful connection."""
        self._connected = True
        self._update_ui_state()
        self._on_refresh_rooms()
        
    def _connection_failed(self, error: str):
        """Handle failed connection."""
        self._connected = False
        self._client = None
        self._update_ui_state()
        messagebox.showerror("Connection Error", error)
        
    def _on_disconnect(self):
        """Handle disconnect button click."""
        if self._client:
            self._client.disconnect()
            self._client = None
            
        self._connected = False
        self._in_room = False
        self._clear_room_list()
        self._clear_participants()
        self._update_ui_state()
        
    def _on_refresh_rooms(self):
        """Handle refresh rooms button click."""
        if not self._client:
            return
            
        def refresh_task():
            try:
                rooms = self._client.list_rooms()
                self.root.after(0, lambda: self._update_room_list(rooms))
            except Exception as e:
                logger.error(f"Error refreshing rooms: {e}")
                
        threading.Thread(target=refresh_task, daemon=True).start()
        
    def _update_room_list(self, rooms: list):
        """Update the room list display."""
        self._clear_room_list()
        
        for room in rooms:
            status = "Locked" if room.get('is_locked') else "Open"
            participants = f"{room.get('participants', 0)}/{room.get('max_participants', 10)}"
            self.room_tree.insert(
                "", tk.END, 
                iid=room.get('id'),
                values=(room.get('name'), participants, status)
            )
            
    def _clear_room_list(self):
        """Clear the room list."""
        for item in self.room_tree.get_children():
            self.room_tree.delete(item)
            
    def _on_create_room(self):
        """Handle create room button click."""
        name = simpledialog.askstring(
            "Create Room", 
            "Enter room name:",
            parent=self.root
        )
        
        if not name:
            return
            
        def create_task():
            try:
                room_id = self._client.create_room(name)
                if room_id:
                    self.root.after(0, self._on_refresh_rooms)
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", "Failed to create room"
                    ))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                
        threading.Thread(target=create_task, daemon=True).start()
        
    def _on_join_room(self):
        """Handle join room button click."""
        selection = self.room_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a room to join")
            return
            
        room_id = selection[0]
        
        def join_task():
            try:
                if self._client.join_room(room_id):
                    self.root.after(0, self._join_success)
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", "Failed to join room"
                    ))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                
        threading.Thread(target=join_task, daemon=True).start()
        
    def _join_success(self):
        """Handle successful room join."""
        self._in_room = True
        self._update_ui_state()
        
    def _on_leave_room(self):
        """Handle leave room button click."""
        if self._client:
            self._client.leave_room()
            
        self._in_room = False
        self._clear_participants()
        self._update_ui_state()
        
    def _on_audio_toggle(self):
        """Handle audio toggle."""
        enabled = self.audio_var.get()
        if self._client:
            self._client.toggle_audio(enabled)
            
    def _on_video_toggle(self):
        """Handle video toggle."""
        enabled = self.video_var.get()
        if self._client:
            self._client.toggle_video(enabled)
            
    def _on_participant_joined(self, participant_id: str, username: str):
        """Handle participant joined event."""
        self.root.after(0, lambda: self._add_participant(username))
        
    def _on_participant_left(self, participant_id: str):
        """Handle participant left event."""
        # Note: Would need to map participant_id to username
        self.root.after(0, self._on_refresh_rooms)
        
    def _on_client_disconnected(self):
        """Handle client disconnection."""
        self.root.after(0, self._handle_disconnect)
        
    def _handle_disconnect(self):
        """Handle disconnection in main thread."""
        self._connected = False
        self._in_room = False
        self._client = None
        self._clear_room_list()
        self._clear_participants()
        self._update_ui_state()
        messagebox.showwarning("Disconnected", "Lost connection to server")
        
    def _add_participant(self, username: str):
        """Add a participant to the list."""
        self.participants_listbox.insert(tk.END, username)
        
    def _clear_participants(self):
        """Clear the participants list."""
        self.participants_listbox.delete(0, tk.END)
        
    def _on_close(self):
        """Handle window close."""
        if self._client:
            self._client.disconnect()
        self.root.destroy()


def main():
    """Main entry point for the GUI application."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run the application
    root = tk.Tk()
    app = PQCChatGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
