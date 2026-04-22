# Shorts Automation

This project is a Python-based automation tool for creating and uploading YouTube Shorts. It streamlines the process of generating video content, from scripting to final upload.

## Features

- **Script Generation:** Automatically generates scripts for the shorts.
- **Video Downloading:** Downloads raw video clips to be used in the composition.
- **Video Composition:** Composes the downloaded clips into a final video.
- **Captioning:** Adds captions to the composed video.
- **Voiceover:** Adds voiceover to the video.
- **Batch Processing:** Can compose multiple videos in a batch.
- **YouTube Uploading:** Uploads the final video to YouTube.

## Project Structure

- `script_generator.py`: Generates the script for the video.
- `downloader.py`: Downloads raw video clips.
- `composer.py`: Composes the video from the raw clips.
- `captioner.py`: Adds captions to the video.
- `voiceover.py`: Adds voiceover to the video.
- `batch_compose.py`: Composes multiple videos in a batch.
- `uploader.py`: Uploads the final video to YouTube.
- `pipeline.py`: Manages the overall workflow of the automation.
- `run.py`: The main script to run the automation.
- `ui.py` and `ui.html`: A simple user interface for the tool.
- `client_secrets.json`: Credentials for the YouTube API.
- `output/`: Directory for the final videos.
- `raw_clips/`: Directory for the downloaded raw clips.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/guvinduwelikala/shorts-automation.git
    ```
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file is not present. You may need to create one based on the imports in the Python files.)*

3.  Set up your YouTube API credentials and save them in `client_secrets.json`.

## Usage

Run the main script to start the automation process:

```bash
python run.py
```

You can also use the user interface by running:

```bash
python ui.py
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License.
