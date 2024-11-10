import customtkinter as ctk
import threading
from datetime import datetime
import os
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from yt_dlp import YoutubeDL
from youtube_search import YoutubeSearch
from tqdm import tqdm
import queue
import tkinter as tk
from tkinter import messagebox
import csv
from pathlib import Path
from CTkToolTip import CTkToolTip

class SpotifyDownloaderGUI:
    def __init__(self):
        ctk.set_default_color_theme("green")
        self.window = ctk.CTk()
        self.window.title("Fuck Spotify")
        self.window.geometry("1200x720")
        
        self.thread_colors = [
            "#FF6B6B",  # Red
            "#4ECDC4",  # Teal
            "#45B7D1",  # Blue
            "#96CEB4",  # Green
            "#FFEEAD",  # Yellow
            "#D4A5A5",  # Pink
            "#9FA8DA",  # Purple
            "#FFE082"   # Orange
        ]
        self.start_time = None
        self.timer_running = False

        # Initialize variables
        self.download_queue = queue.Queue()
        self.current_downloads = []
        self.download_threads = []
        self.playlists = []  # Store playlist data
        self.selected_playlist = None
        self.output_queue = queue.Queue() 
        
        # Create temp directory
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Create main container
        self.create_gui_elements()
        
        # Initialize Spotify client
        self.sp = None
        self.initialize_spotify()

        # Start output update timer
        self.update_output_display()

    def create_gui_elements(self):
        self.create_sidebar()
        self.create_main_area() 
    
    def create_sidebar(self):
        # Create sidebar frame
        self.sidebar = ctk.CTkFrame(
            self.window,
            width=300
        )
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)
        self.sidebar.pack_propagate(False)  # Prevent sidebar from shrinking
        
        # App title in sidebar
        self.title_label = ctk.CTkLabel(
            self.sidebar,
            text="Fuck Spotify",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.pack(pady=20)
        
        # Authentication Frame in sidebar
        self.auth_frame = ctk.CTkFrame(self.sidebar)
        self.auth_frame.pack(padx=10, pady=10, fill="x")
        
        # Client ID
        self.client_id_label = ctk.CTkLabel(
            self.auth_frame,
            text="Client ID:"
        )
        self.client_id_label.pack(padx=5, pady=(5,0))
        
        self.client_id_entry = ctk.CTkEntry(
            self.auth_frame,
            width=250
        )
        self.client_id_entry.pack(padx=5, pady=(0,5))
        CTkToolTip(self.client_id_entry, 
                   message="Enter your Spotify Client ID from the Developer Dashboard")
        
        # Client Secret
        self.client_secret_label = ctk.CTkLabel(
            self.auth_frame,
            text="Client Secret:"
        )
        self.client_secret_label.pack(padx=5, pady=(5,0))
        
        self.client_secret_entry = ctk.CTkEntry(
            self.auth_frame,
            width=250,
            show="•"  # Hide secret with dots
        )
        self.client_secret_entry.pack(padx=5, pady=(0,5))
        CTkToolTip(self.client_secret_entry, 
                   message="Enter your Spotify Client Secret from the Developer Dashboard")
        
        # Authentication button
        self.auth_button = ctk.CTkButton(
            self.auth_frame,
            text="Authenticate",
            command=self.initialize_spotify
        )
        self.auth_button.pack(padx=5, pady=10)
        
        # Settings section in sidebar
        self.settings_frame = ctk.CTkFrame(self.sidebar)
        self.settings_frame.pack(padx=10, pady=10, fill="x")
        
        self.settings_label = ctk.CTkLabel(
            self.settings_frame,
            text="Download Settings",
            font=ctk.CTkFont(weight="bold")
        )
        self.settings_label.pack(pady=5)
        
        # Thread control
        self.thread_label = ctk.CTkLabel(
            self.settings_frame,
            text="Download Threads:"
        )
        self.thread_label.pack(pady=2)
        
        self.thread_slider = ctk.CTkSlider(
            self.settings_frame,
            from_=1,
            to=8,
            number_of_steps=7
        )
        self.thread_slider.pack(pady=2)
        self.thread_slider.set(4)
        
        self.thread_value_label = ctk.CTkLabel(
            self.settings_frame,
            text="4"
        )
        self.thread_value_label.pack(pady=2)
        self.thread_slider.configure(
            command=self.update_thread_value
        )

        self.system_check_frame = ctk.CTkFrame(self.sidebar)
        self.system_check_frame.pack(padx=10, pady=10, fill="x", side="bottom")
        
        self.check_system_button = ctk.CTkButton(
            self.system_check_frame,
            text="Check System Requirements",
            command=self.check_system_requirements
        )
        self.check_system_button.pack(padx=5, pady=5)
        
        # Status label for system checks
        self.system_status_label = ctk.CTkLabel(
            self.system_check_frame,
            text="System status: Not checked",
            wraplength=280  # Wrap text to fit sidebar
        )
        self.system_status_label.pack(padx=5, pady=5)

    def create_main_area(self):
        # Create main content area
        self.main_area = ctk.CTkFrame(self.window)
        self.main_area.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # Create TabView
        self.tabview = ctk.CTkTabview(self.main_area)
        self.tabview.pack(fill="both", expand=True)
        
        # Create tabs
        self.playlist_tab = self.tabview.add("Playlists")
        self.downloads_tab = self.tabview.add("Downloads")
        self.logs_tab = self.tabview.add("Logs")
        
        # Playlist Tab Content
        self.create_playlist_tab()
        
        # Downloads Tab Content
        self.create_downloads_tab()
        
        # Logs Tab Content
        self.create_logs_tab()

    def create_playlist_tab(self):
        # Playlist selection area
        self.playlist_label = ctk.CTkLabel(
            self.playlist_tab,
            text="Available Playlists:",
            font=ctk.CTkFont(weight="bold")
        )
        self.playlist_label.pack(padx=10, pady=5)
        
        # Create scrollable frame for playlists
        self.playlist_scrollable = ctk.CTkScrollableFrame(
            self.playlist_tab,
            height=400
        )
        self.playlist_scrollable.pack(padx=10, pady=5, fill="both", expand=True)
        
        # Dictionary to store checkbox references
        self.playlist_checkboxes = {}

    def create_downloads_tab(self):
        # Progress information
        self.progress_label = ctk.CTkLabel(
            self.downloads_tab,
            text="Ready to download"
        )
        self.progress_label.pack(pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.downloads_tab)
        self.progress_bar.pack(pady=5, fill="x", padx=20)
        self.progress_bar.set(0)
        
        self.download_button = ctk.CTkButton(
            self.downloads_tab,
            text="Start Download",
            command=self.start_download_process
        )
        self.download_button.pack(pady=5)
        
        # Current downloads display
        self.downloads_output = ctk.CTkTextbox(
            self.downloads_tab,
            height=200,
            wrap="word"
        )
        self.downloads_output.pack(padx=20, pady=5, fill="both", expand=True)
        self.downloads_output.configure(state="disabled")
        
        self.clear_downloads_button = ctk.CTkButton(
            self.downloads_tab,
            text="Clear Download History",
            command=lambda: self.clear_output(self.downloads_output)
        )
        self.clear_downloads_button.pack(pady=5)
    
    def create_logs_tab(self):
        # Create timer frame at top
        self.timer_frame = ctk.CTkFrame(self.logs_tab)
        self.timer_frame.pack(padx=20, pady=5, fill="x")
        
        self.elapsed_label = ctk.CTkLabel(
            self.timer_frame,
            text="Time Elapsed: 00:00:00",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.elapsed_label.pack(pady=5)
        
        # Log display with tags for colors
        self.output_text = ctk.CTkTextbox(
            self.logs_tab,
            wrap="word"
        )
        self.output_text.pack(padx=20, pady=5, fill="both", expand=True)
        self.output_text.configure(state="disabled")
        
        # Create tags for each thread color
        for i, color in enumerate(self.thread_colors):
            self.output_text.tag_config(f'thread_{i+1}', foreground=color)
        
        # Default tag for non-thread messages
        self.output_text.tag_config('default', foreground="white")
        
        self.clear_logs_button = ctk.CTkButton(
            self.logs_tab,
            text="Clear Logs",
            command=lambda: self.clear_output(self.output_text)
        )
        self.clear_logs_button.pack(pady=5)
        
    
    def update_timer(self):
        """Update the elapsed time display"""
        if self.start_time and self.timer_running:
            elapsed = datetime.now() - self.start_time
            # Convert to hours, minutes, seconds
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"Time Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}"
            self.elapsed_label.configure(text=time_str)
            self.window.after(1000, self.update_timer)  # Update every second

    def update_thread_value(self, value):
        threads = int(value)
        self.thread_value_label.configure(text=str(threads))
        # Update tooltip to show current value and recommendation
        recommendation = "Light load" if threads <= 3 else "Balanced" if threads <= 6 else "Heavy load"
        CTkToolTip(self.thread_slider, 
                   message=f"Current: {threads} threads - {recommendation}\nMore threads = faster but more resource intensive")
        

    def clear_output(self, textbox):
        """Clear the specified textbox and reset timer"""
        # Clear textbox
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.configure(state="disabled")
        
        # Reset timer
        self.timer_running = False
        self.start_time = None
        self.elapsed_label.configure(text="Time Elapsed: 00:00:00")

    def add_output(self, message, is_download=False, thread_id=None):
        """Add message to output queue"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.output_queue.put((formatted_message, is_download, thread_id))

    def update_output_display(self):
        """Update both output displays with queued messages"""
        try:
            while True:
                message, is_download, thread_id = self.output_queue.get_nowait()
                
                # Update logs tab with color
                self.output_text.configure(state="normal")
                start_index = self.output_text.index("end-1c")
                self.output_text.insert("end", message)
                end_index = self.output_text.index("end-1c")
                
                # Apply color tag based on thread ID
                if thread_id is not None:
                    # Use modulo to cycle through colors if more threads than colors
                    color_index = (thread_id - 1) % len(self.thread_colors)
                    self.output_text.tag_add(f'thread_{thread_id}', start_index, end_index)
                else:
                    self.output_text.tag_add('default', start_index, end_index)
                
                self.output_text.see("end")
                self.output_text.configure(state="disabled")
                
                # Update downloads tab if it's a download message
                if is_download:
                    self.downloads_output.configure(state="normal")
                    self.downloads_output.insert("end", message)
                    self.downloads_output.see("end")
                    self.downloads_output.configure(state="disabled")
                    
        except queue.Empty:
            pass
        finally:
            # Schedule next update
            self.window.after(100, self.update_output_display)

    
    def reset_states(self):
        """Reset all states after download completion"""
        # Reset progress bar and label
        self.progress_bar.set(0)
        self.progress_label.configure(text="Ready to download")
        
        self.timer_running = False

        # Enable download button in downloads tab
        self.download_button.configure(state="normal")
        
        # Re-enable playlist selection
        for checkbox_data in self.playlist_checkboxes.values():
            checkbox = checkbox_data['checkbox']
            checkbox.configure(state="normal")
            if checkbox_data['var'].get():
                checkbox.deselect()
        
        # Clear selected playlist
        self.selected_playlist = None
        
        # Clear current downloads list
        self.current_downloads.clear()
        
        # Add completion message to output
        self.add_output("Download process completed. Ready for next download.")
        
    def on_playlist_select(self, playlist):
        """Handle playlist selection"""
        checkbox_data = self.playlist_checkboxes[playlist['id']]
        
        # Deselect all other checkboxes
        for pid, data in self.playlist_checkboxes.items():
            if pid != playlist['id'] and data['var'].get():
                data['checkbox'].deselect()
        
        # Update selected playlist
        if checkbox_data['var'].get():
            self.selected_playlist = playlist
        else:
            self.selected_playlist = None
            
    def create_labeled_entry(self, parent, label_text, row):
        label = ctk.CTkLabel(parent, text=label_text)
        label.grid(row=row, column=0, padx=5, pady=5)
        
        entry = ctk.CTkEntry(parent, width=300)
        entry.grid(row=row, column=1, padx=5, pady=5)
        
        return entry

    def initialize_spotify(self):
        try:
            # Check for existing cache file in current directory
            cache_path = '.cache'
            
            # If cache exists and is valid, try to use it first
            if os.path.exists(cache_path):
                try:
                    # Try to initialize with existing cache
                    self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                        redirect_uri='http://localhost:8888/callback',
                        scope='user-library-read playlist-read-private'
                    ))
                    
                    # Test the connection
                    self.sp.current_user()
                    
                    # If successful, update UI and fetch playlists
                    self.add_output("Successfully authenticated with cached credentials")
                    messagebox.showinfo(
                        "Success", 
                        "Successfully authenticated with cached credentials!"
                    )
                    self.fetch_playlists()
                    return
                    
                except Exception as cache_error:
                    self.add_output(f"Cached credentials invalid or expired: {str(cache_error)}")
                    # If cache authentication fails, continue to manual authentication
                    try:
                        os.remove(cache_path)
                        self.add_output("Removed invalid cache file")
                    except:
                        pass
            
            # If no cache or cache failed, check for client credentials
            client_id = self.client_id_entry.get()
            client_secret = self.client_secret_entry.get()
            
            if not client_id or not client_secret:
                messagebox.showerror(
                    "Error", 
                    "Please enter both Client ID and Client Secret"
                )
                return

            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri='http://localhost:8888/callback',
                scope='user-library-read playlist-read-private'
            ))
            
            # Test the connection
            self.sp.current_user()
            self.add_output("Successfully authenticated with provided credentials")
            messagebox.showinfo(
                "Success", 
                "Successfully authenticated with Spotify!"
            )
            
            # Get user's playlists
            self.fetch_playlists()
            
        except Exception as e:
            self.add_output(f"Authentication failed: {str(e)}")
            messagebox.showerror("Error", f"Authentication failed: {str(e)}")

    def fetch_playlists(self):
        try:
            results = self.sp.current_user_playlists()
            self.playlists = results['items']
            
            # Clear existing checkboxes
            for widget in self.playlist_scrollable.winfo_children():
                widget.destroy()
            self.playlist_checkboxes.clear()
            
            # Create new checkboxes for each playlist
            for playlist in self.playlists:
                var = ctk.BooleanVar()
                checkbox = ctk.CTkCheckBox(
                    self.playlist_scrollable,
                    text=f"{playlist['name']} ({playlist['tracks']['total']} tracks)",
                    variable=var,
                    command=lambda p=playlist: self.on_playlist_select(p)
                )
                checkbox.pack(padx=10, pady=5, anchor="w")
                self.playlist_checkboxes[playlist['id']] = {
                    'checkbox': checkbox,
                    'var': var,
                    'playlist': playlist
                }
                
                # Add tooltip with playlist details
                CTkToolTip(checkbox, 
                          message=f"Playlist: {playlist['name']}\n"
                                 f"Tracks: {playlist['tracks']['total']}\n"
                                 f"Owner: {playlist['owner']['display_name']}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch playlists: {str(e)}")

    def save_tracks_to_csv(self, tracks, playlist_name):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = self.temp_dir / f"playlist_{playlist_name}_{timestamp}.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'Track Name', 'Artists', 'Album', 'Track ID', 
                'Spotify URL', 'Download Status'
            ])
            writer.writeheader()
            for track in tracks:
                track['Download Status'] = 'Pending'
                writer.writerow(track)
        
        return csv_path

    def update_track_status(self, csv_path, track_id, status):
        df = pd.read_csv(csv_path)
        df.loc[df['Track ID'] == track_id, 'Download Status'] = status
        df.to_csv(csv_path, index=False)

    def download_worker(self, worker_id, csv_path):
        try:
            while True:
                try:
                    track = self.download_queue.get_nowait()
                    
                    # Update progress label and add to output
                    status_message = f"Thread {worker_id}: Downloading {track['Track Name']} by {track['Artists']}"
                    self.window.after(0, self.progress_label.configure, {
                        "text": status_message
                    })
                    self.add_output(status_message, is_download=True, thread_id=worker_id)
                    
                    # Download the track
                    success = self.download_track(track)
                    
                    # Update CSV status and add to output
                    status = 'Completed' if success else 'Failed'
                    self.update_track_status(csv_path, track['Track ID'], status)
                    
                    completion_message = (f"Thread {worker_id}: {status} - {track['Track Name']}"
                                    f"{' ✓' if success else ' ✗'}")
                    self.add_output(completion_message, is_download=True, thread_id=worker_id)
                    
                    # Update progress bar
                    progress = (len(self.current_downloads) - 
                            self.download_queue.qsize()) / len(self.current_downloads)
                    self.window.after(0, self.progress_bar.set, progress)
                    
                    self.download_queue.task_done()
                    
                except queue.Empty:
                    break
                
            self.add_output(f"Thread {worker_id}: Finished all tasks", is_download=True, thread_id=worker_id)
            
        finally:
            # When thread is finishing, schedule a check for all threads
            self.window.after(0, self.check_thread_completion)


    def check_thread_completion(self):
        """Check if all download threads have completed and reset if they have"""
        if all(not thread.is_alive() for thread in self.download_threads):
            # All threads are done, schedule reset_states
            self.window.after(100, self.reset_states)
        else:
            # Some threads still running, check again in 100ms
            self.window.after(100, self.check_thread_completion)

    def start_download_process(self):
        if not self.selected_playlist:
            messagebox.showerror("Error", "Please select a playlist first")
            return
        
        self.start_time = datetime.now()
        self.timer_running = True
        self.update_timer()

        # Get the checkbox for selected playlist
        checkbox_data = self.playlist_checkboxes[self.selected_playlist['id']]
        checkbox = checkbox_data['checkbox']
        
        # Disable checkbox during download
        
        checkbox.configure(state="disabled")

        # Create downloads directory
        os.makedirs('downloads', exist_ok=True)

        # Disable download button
        self.download_button.configure(state="disabled")
        self.progress_label.configure(text="Fetching playlist tracks...")

        # Start download process in separate thread
        def download_process():
            try:
                # Get tracks from playlist
                tracks = self.get_playlist_tracks(self.selected_playlist['id'])
                self.current_downloads = tracks

                
                # Save tracks to CSV
                csv_path = self.save_tracks_to_csv(
                    tracks, 
                    self.selected_playlist['name']
                )

                # Clear existing queue and add tracks
                while not self.download_queue.empty():
                    self.download_queue.get()
                
                for track in tracks:
                    self.download_queue.put(track)

                # Clear existing threads
                self.download_threads.clear()

                # Start download worker threads
                num_threads = int(self.thread_slider.get())
                for i in range(num_threads):
                    thread = threading.Thread(
                        target=self.download_worker,
                        args=(i + 1, csv_path),
                        daemon=True
                    )
                    self.download_threads.append(thread)
                    thread.start()

            except Exception as e:
                self.window.after(0, messagebox.showerror, "Error", str(e))
                self.window.after(0, self.download_button.configure, {
                    "state": "normal"
                })
                self.window.after(0, checkbox.configure, {"state": "normal"})

        thread = threading.Thread(target=download_process, daemon=True)
        thread.start()

    def get_playlist_tracks(self, playlist_id):
        tracks = []
        offset = 0
        
        while True:
            results = self.sp.playlist_tracks(
                playlist_id,
                offset=offset,
                fields="items(track(name,artists,album(name),duration_ms,id,external_urls))"
            )
            
            if not results['items']:
                break
                
            for item in results['items']:
                track = item['track']
                if track is None:
                    continue
                    
                artists = ", ".join([artist['name'] for artist in track['artists']])
                
                track_info = {
                    'Track Name': track['name'],
                    'Artists': artists,
                    'Album': track['album']['name'],
                    'Track ID': track['id'],
                    'Spotify URL': track['external_urls']['spotify']
                }
                tracks.append(track_info)
                
            offset += len(results['items'])
            
        return tracks

    def search_youtube(self, song_name, artist):
        try:
            query = f"{song_name} {artist} official audio"
            results = YoutubeSearch(query, max_results=1).to_dict()
            
            if results:
                return f"https://youtube.com{results[0]['url_suffix']}"
            return None
            
        except Exception as e:
            print(f"Error searching YouTube: {str(e)}")
            return None

    def download_track(self, track_info):
        video_url = self.search_youtube(
            track_info['Track Name'],
            track_info['Artists']
        )
        
        if not video_url:
            self.add_output(f"Failed to find YouTube URL for: {track_info['Track Name']}")
            return False

        try:
            # Create sanitized playlist folder name
            playlist_name = "".join(
                x for x in self.selected_playlist['name']
                if x.isalnum() or x in [' ', '-', '_']
            ).rstrip()
            
            # Create playlist directory
            playlist_dir = os.path.join('downloads', playlist_name)
            os.makedirs(playlist_dir, exist_ok=True)
            
            # Create sanitized filename
            filename = f"{track_info['Track Name']} - {track_info['Artists']}"
            filename = "".join(
                x for x in filename 
                if x.isalnum() or x in [' ', '-', '_']
            ).rstrip()
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(playlist_dir, f'{filename}.%(ext)s'),
                'quiet': True,
                'no_warnings': True
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            return True
            
        except Exception as e:
            error_message = f"Error downloading {filename}: {str(e)}"
            self.add_output(error_message)
            return False
        
    def check_system_requirements(self):
        """Check if all required system dependencies are available"""
        requirements_met = True
        status_messages = []
        
        # Check FFmpeg
        if not self.check_ffmpeg():
            requirements_met = False
            status_messages.append("❌ FFmpeg not found - Required for audio conversion")
        else:
            status_messages.append("✓ FFmpeg installed")
        
        # Check python packages
        required_packages = {
            'yt_dlp': 'youtube-dl',
            'spotipy': 'spotipy',
            'customtkinter': 'customtkinter',
            'youtube_search': 'youtube-search'
        }
        
        for package, pip_name in required_packages.items():
            if not self.check_package(package):
                requirements_met = False
                status_messages.append(f"❌ {pip_name} not found - pip install {pip_name}")
            else:
                status_messages.append(f"✓ {pip_name} installed")
        
        # Check temp directory
        if not os.path.exists(self.temp_dir):
            try:
                os.makedirs(self.temp_dir)
                status_messages.append("✓ Temp directory created")
            except Exception as e:
                requirements_met = False
                status_messages.append("❌ Could not create temp directory")
        else:
            status_messages.append("✓ Temp directory exists")
        
        # Check main downloads directory
        if not os.path.exists('downloads'):
            try:
                os.makedirs('downloads')
                status_messages.append("✓ Downloads directory created")
            except Exception as e:
                requirements_met = False
                status_messages.append("❌ Could not create downloads directory")
        else:
            status_messages.append("✓ Downloads directory exists")
        
        # Update status label
        status_text = "System status:\n" + "\n".join(status_messages)
        if requirements_met:
            status_text += "\n\n✅ All requirements satisfied!"
            self.system_status_label.configure(
                text=status_text,
                text_color="green"
            )
        else:
            status_text += "\n\n❌ Some requirements missing!"
            self.system_status_label.configure(
                text=status_text,
                text_color="red"
            )

    def check_ffmpeg(self):
        """Check if FFmpeg is installed and accessible"""
        try:
            # Try both ffmpeg and ffmpeg.exe for Windows
            if os.system('ffmpeg -version') == 0:
                return True
            if os.system('ffmpeg.exe -version') == 0:
                return True
            return False
        except:
            return False

    def check_package(self, package_name):
        """Check if a Python package is installed"""
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = SpotifyDownloaderGUI()
    app.run()