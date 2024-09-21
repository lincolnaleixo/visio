# Video Motion Detector

This project is a Python-based tool for detecting motion in video files and creating new videos containing only the segments with detected motion.

## Features

- Processes video files to detect motion
- Creates new video files containing only segments with detected motion
- Preserves original file metadata (access and modification times)
- Supports multiple video formats (mp4, avi, mov, mkv, flv, wmv, mpeg)
- Deletes original video files after processing
- Handles multiple videos in parallel using multiprocessing

## Requirements

- Python 3.12
- OpenCV
- PyAV
- FFmpeg

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/video-motion-detector.git
   cd video-motion-detector
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Ensure FFmpeg is installed on your system.

## Usage

1. Place your video files in the `videos` directory.

2. Run the main script:
   ```
   python app.py
   ```

3. Processed videos with motion will be saved in the `output` directory.

## Configuration

The application uses environment variables for configuration. Copy the `.env.example` file to `.env` and adjust the values as needed:

```bash
cp .env.example .env
```

Then edit the `.env` file with your specific settings:

- `MIN_CONTOUR_AREA`: Minimum contour area for motion detection (default: 500)
- `BUFFER_TIME`: Buffer time in seconds to add before and after detected motion (default: 2)
- `INPUT_FOLDER`: Folder containing input videos (default: 'videos')
- `OUTPUT_FOLDER`: Folder for processed output videos (default: 'output')

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- OpenCV for computer vision capabilities
- PyAV for video processing
- FFmpeg for video encoding and decoding
