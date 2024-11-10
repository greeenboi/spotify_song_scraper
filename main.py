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
        self.window = ctk.CTk()
        self.window.title("Spotify Playlist Downloader")
        self.window.geometry("800x600")
        
        # Initialize variables
        self.download_queue = queue.Queue()
        self.current_downloads = []
        self.download_threads = []
        self.playlists = []  # Store playlist data
        self.selected_playlist = None
        
        # Create temp directory
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Create main container
        self.create_gui_elements()
        
        # Initialize Spotify client
        self.sp = None
        self.initialize_spotify()

    def create_gui_elements(self):
        # Create frames
        self.auth_frame = ctk.CTkFrame(self.window)
        self.auth_frame.pack(padx=20, pady=20, fill="x")
        
        self.playlist_frame = ctk.CTkFrame(self.window)
        self.playlist_frame.pack(padx=20, pady=(0, 20), fill="both", expand=True)
        
        self.settings_frame = ctk.CTkFrame(self.window)
        self.settings_frame.pack(padx=20, pady=(0, 20), fill="x")
        
        self.download_frame = ctk.CTkFrame(self.window)
        self.download_frame.pack(padx=20, pady=(0, 20), fill="x")

        # Authentication Frame Elements
        self.client_id_entry = self.create_labeled_entry(
            self.auth_frame, "Client ID:", 0)
        CTkToolTip(self.client_id_entry, 
                   message="Enter your Spotify Client ID from the Spotify Developer Dashboard")
        
        self.client_secret_entry = self.create_labeled_entry(
            self.auth_frame, "Client Secret:", 1)
        CTkToolTip(self.client_secret_entry, 
                   message="Enter your Spotify Client Secret from the Spotify Developer Dashboard")
        
        self.auth_button = ctk.CTkButton(
            self.auth_frame, 
            text="Authenticate", 
            command=self.initialize_spotify
        )
        self.auth_button.grid(row=2, column=0, columnspan=2, pady=10)
        CTkToolTip(self.auth_button, 
                   message="Click to authenticate with Spotify using your credentials")

        # Playlist Frame Elements
        self.playlist_label = ctk.CTkLabel(
            self.playlist_frame,
            text="Select Playlist:"
        )
        self.playlist_label.pack(padx=10, pady=5)
        
        self.playlist_listbox = tk.Listbox(
            self.playlist_frame,
            selectmode=tk.SINGLE,
            height=10
        )
        self.playlist_listbox.pack(padx=10, pady=5, fill="both", expand=True)
        self.playlist_listbox.bind('<<ListboxSelect>>', self.on_playlist_select)
        
        # Settings Frame Elements
        self.thread_label = ctk.CTkLabel(
            self.settings_frame,
            text="Number of download threads:"
        )
        self.thread_label.pack(pady=5)
        
        self.thread_slider = ctk.CTkSlider(
            self.settings_frame,
            from_=1,
            to=8,
            number_of_steps=7
        )
        self.thread_slider.pack(pady=5)
        self.thread_slider.set(4)  # Default to 4 threads
        CTkToolTip(self.thread_slider, 
                   message="Adjust the number of simultaneous downloads (1-8)\nMore threads = faster but more resource intensive")
        
        self.thread_value_label = ctk.CTkLabel(
            self.settings_frame,
            text="4"
        )
        self.thread_value_label.pack(pady=5)
        self.thread_slider.configure(
            command=self.update_thread_value
        )
        
        # Download Frame Elements
        self.progress_label = ctk.CTkLabel(
            self.download_frame,
            text="Ready to download"
        )
        self.progress_label.pack(pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.download_frame)
        self.progress_bar.pack(pady=5, fill="x")
        self.progress_bar.set(0)
        CTkToolTip(self.progress_bar, 
                   message="Shows current download progress")
        
        self.download_button = ctk.CTkButton(
            self.download_frame,
            text="Start Download",
            command=self.start_download_process
        )
        self.download_button.pack(pady=5)
        CTkToolTip(self.download_button, 
                   message="Click to start downloading the selected playlist\nFiles will be saved to /downloads folder")

    def update_thread_value(self, value):
        threads = int(value)
        self.thread_value_label.configure(text=str(threads))
        # Update tooltip to show current value and recommendation
        recommendation = "Light load" if threads <= 3 else "Balanced" if threads <= 6 else "Heavy load"
        CTkToolTip(self.thread_slider, 
                   message=f"Current: {threads} threads - {recommendation}\nMore threads = faster but more resource intensive")
        
    def on_playlist_select(self, event):
        selection = self.playlist_listbox.curselection()
        if selection:
            self.selected_playlist = self.playlists[selection[0]]
            
    def create_labeled_entry(self, parent, label_text, row):
        label = ctk.CTkLabel(parent, text=label_text)
        label.grid(row=row, column=0, padx=5, pady=5)
        
        entry = ctk.CTkEntry(parent, width=300)
        entry.grid(row=row, column=1, padx=5, pady=5)
        
        return entry

    def initialize_spotify(self):
        try:
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
            messagebox.showinfo(
                "Success", 
                "Successfully authenticated with Spotify!"
            )
            
            # Get user's playlists
            self.fetch_playlists()
            
        except Exception as e:
            messagebox.showerror("Error", f"Authentication failed: {str(e)}")

    def fetch_playlists(self):
        try:
            results = self.sp.current_user_playlists()
            self.playlists = results['items']
            
            # Clear and update playlist listbox
            self.playlist_listbox.delete(0, tk.END)
            for playlist in self.playlists:
                self.playlist_listbox.insert(
                    tk.END, 
                    f"{playlist['name']} ({playlist['tracks']['total']} tracks)"
                )
                
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
        while True:
            try:
                track = self.download_queue.get_nowait()
                
                # Update progress label
                self.window.after(0, self.progress_label.configure, {
                    "text": f"Thread {worker_id}: Downloading {track['Track Name']}"
                })
                
                # Download the track
                success = self.download_track(track)
                
                # Update CSV status
                status = 'Completed' if success else 'Failed'
                self.update_track_status(csv_path, track['Track ID'], status)
                
                # Update progress bar
                progress = (len(self.current_downloads) - 
                          self.download_queue.qsize()) / len(self.current_downloads)
                self.window.after(0, self.progress_bar.set, progress)
                
                self.download_queue.task_done()
                
            except queue.Empty:
                break
        
        # Enable download button when all threads complete
        if all(not thread.is_alive() for thread in self.download_threads):
            self.window.after(0, self.download_button.configure, {"state": "normal"})
            self.window.after(0, self.progress_label.configure, {
                "text": "Download complete!"
            })

    def start_download_process(self):
        if not self.selected_playlist:
            messagebox.showerror("Error", "Please select a playlist first")
            return

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
            return False

        try:
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
                'outtmpl': f'downloads/{filename}.%(ext)s',
                'quiet': True,
                'no_warnings': True
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            return True
            
        except Exception as e:
            print(f"Error downloading {filename}: {str(e)}")
            return False

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = SpotifyDownloaderGUI()
    app.run()