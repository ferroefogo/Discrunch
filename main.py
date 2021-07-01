import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import PIL
from PIL import Image
import os
import glob
import ffmpeg


class App():
    def __init__(self, master):
        self.master = master

        # Window parameters
        master.title('Discrunch')
        master.configure(bg='gray15')
        master.option_add('*foreground', 'yellow')
        master.option_add('*background', 'gray15')
        master.geometry('500x500')

        # TITLE GRAPHIC
        titleframe = tk.Frame(master)
        titleframe.pack(fill=tk.X, anchor=tk.N)

        title_text = tk.Label(titleframe, text="DISCRUNCH", font="System 36 bold")
        title_text.pack()

        title_subtext = tk.Label(titleframe, text="Crunch your media", font="System 4 italic", fg="white")
        title_subtext.pack()

        # Main Frame (pun intended)
        mainframe = tk.Frame(master)
        mainframe.pack(fill=tk.BOTH, side=tk.TOP, anchor=tk.N)

        # Directory Browser Container
        directory_browse_container = tk.Frame(mainframe)
        directory_browse_container.pack(fill=tk.BOTH, expand=True)

        # Click Browse to search and enter a file.
        browsebutton = tk.Button(directory_browse_container, text="Browse", command=self.browsefunc)
        browsebutton.pack()

        self.directory_default_var = tk.StringVar()
        self.directory_default_var.set('~/Downloads')

        self.default_directory = ttk.Entry(directory_browse_container, textvariable=self.directory_default_var)
        self.default_directory.pack()

    def browsefunc(self):
        filepath = filedialog.askopenfilename(initialdir="~/Downloads", title='Please select a directory.')
        filename = os.path.split(filepath)[1]
        print(filepath)

        if filename.endswith(".mp4"):
            self.compress_video(filepath, 6 * 1000)
        else:
            picture = Image.open(filename)
            picture.save("crunch_"+filename, optimize=True, quality=1)

    # Video compression algo.
    def compress_video(self, video_full_path, size_upper_bound, two_pass=True, filename_prefix='crunch_'):
        """
        Compress video file to max-supported size.
        :param video_full_path: the video you want to compress.
        :param size_upper_bound: Max video size in KB.
        :param two_pass: Set to True to enable two-pass calculation.
        :param filename_suffix: Add a suffix for new video.
        :return: out_put_name or error
        """
        filename, extension = os.path.splitext(video_full_path)
        extension = '.mp4'
        output_file_name = filename + filename_prefix + extension

        total_bitrate_lower_bound = 11000
        min_audio_bitrate = 32000
        max_audio_bitrate = 256000
        min_video_bitrate = 100000

        try:
            # Bitrate reference: https://en.wikipedia.org/wiki/Bit_rate#Encoding_bit_rate
            probe = ffmpeg.probe(video_full_path)
            # Video duration, in s.
            duration = float(probe['format']['duration'])
            # Audio bitrate, in bps.
            audio_bitrate = float(next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)['bit_rate'])
            # Target total bitrate, in bps.
            target_total_bitrate = (size_upper_bound * 1024 * 8) / (1.073741824 * duration)
            if target_total_bitrate < total_bitrate_lower_bound:
                print('Bitrate is extremely low! Stop compress!')
                return False

            # Best min size, in kB.
            best_min_size = (min_audio_bitrate + min_video_bitrate) * (1.073741824 * duration) / (8 * 1024)
            if size_upper_bound < best_min_size:
                print('Quality not good! Recommended minimum size:', '{:,}'.format(int(best_min_size)), 'KB.')
                # return False

            # Target audio bitrate, in bps.
            audio_bitrate = audio_bitrate

            # target audio bitrate, in bps
            if 10 * audio_bitrate > target_total_bitrate:
                audio_bitrate = target_total_bitrate / 10
                if audio_bitrate < min_audio_bitrate < target_total_bitrate:
                    audio_bitrate = min_audio_bitrate
                elif audio_bitrate > max_audio_bitrate:
                    audio_bitrate = max_audio_bitrate

            # Target video bitrate, in bps.
            video_bitrate = target_total_bitrate - audio_bitrate
            if video_bitrate < 1000:
                print('Bitrate {} is extremely low! Stop compress.'.format(video_bitrate))
                return False

            i = ffmpeg.input(video_full_path)
            if two_pass:
                ffmpeg.output(i, '/dev/null' if os.path.exists('/dev/null') else 'NUL',
                              **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 1, 'f': 'mp4'}
                              ).overwrite_output().run()
                ffmpeg.output(i, output_file_name,
                              **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 2, 'c:a': 'aac', 'b:a': audio_bitrate}
                              ).overwrite_output().run()
            else:
                ffmpeg.output(i, output_file_name,
                              **{'c:v': 'libx264', 'b:v': video_bitrate, 'c:a': 'aac', 'b:a': audio_bitrate}
                              ).overwrite_output().run()

            if os.path.getsize(output_file_name) <= size_upper_bound * 1024:
                return output_file_name
            elif os.path.getsize(output_file_name) < os.path.getsize(video_full_path):  # Do it again
                return self.compress_video(output_file_name, size_upper_bound)
            else:
                return False
        except FileNotFoundError as e:
            print('You do not have ffmpeg installed!', e)
            print('You can install ffmpeg by reading https://github.com/kkroening/ffmpeg-python/issues/251')
            return False


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
