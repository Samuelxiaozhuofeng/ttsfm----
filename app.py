"""
Flask web application for TTSFM text-to-speech service
"""
from flask import Flask, render_template, request, jsonify, send_file
from ttsfm import TTSClient, Voice, AudioFormat
import os
import uuid
from datetime import datetime
import tempfile
from library import Library

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Initialize TTSFM client
tts_client = TTSClient()

# Initialize Library
library = Library()

# Available voices
VOICES = {
    'alloy': Voice.ALLOY,
    'echo': Voice.ECHO,
    'fable': Voice.FABLE,
    'onyx': Voice.ONYX,
    'nova': Voice.NOVA,
    'shimmer': Voice.SHIMMER
}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_speech():
    """Generate speech from text"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        voice_name = data.get('voice', 'alloy')
        speed = float(data.get('speed', 1.0))
        action = data.get('action', 'download')  # 'download' or 'play'

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Get voice
        voice = VOICES.get(voice_name, Voice.ALLOY)

        # Check text length - if longer than 1000 chars, use long text method
        text_length = len(text)

        if text_length > 1000:
            # Use long text method with auto-combine
            print(f"Processing long text ({text_length} characters) with auto-combine...")
            response = tts_client.generate_speech_long_text(
                text=text,
                voice=voice,
                response_format=AudioFormat.MP3,
                speed=speed,
                max_length=1000,
                preserve_words=True,
                auto_combine=True  # Automatically combine chunks into single file
            )
        else:
            # Use regular method for short text
            response = tts_client.generate_speech(
                text=text,
                voice=voice,
                response_format=AudioFormat.MP3,
                speed=speed,
                validate_length=False
            )

        # Generate unique filename (without extension, save_to_file will add it)
        filename_base = f"tts_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        filepath_base = os.path.join(app.config['OUTPUT_FOLDER'], filename_base)

        # Save to file (this will add the correct extension)
        response.save_to_file(filepath_base)

        # Get the actual filename with extension
        actual_extension = response.format.value
        actual_filename = f"{filename_base}.{actual_extension}"

        return jsonify({
            'success': True,
            'filename': actual_filename,
            'message': f'Speech generated successfully ({text_length} characters)',
            'text_length': text_length,
            'is_long_text': text_length > 1000
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and process text file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file content
        content = file.read().decode('utf-8')
        
        return jsonify({
            'success': True,
            'text': content,
            'message': 'File uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    """Download generated audio file"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            filepath,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/play/<filename>')
def play_file(filename):
    """Stream audio file for playback"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            filepath,
            mimetype='audio/mpeg'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/voices')
def get_voices():
    """Get available voices"""
    return jsonify({
        'voices': list(VOICES.keys())
    })

# ============ Library/Reader Routes ============

@app.route('/reader')
def reader_page():
    """Render the reader page"""
    return render_template('reader.html')

@app.route('/library')
def library_page():
    """Render the library/bookshelf page"""
    return render_template('library.html')

@app.route('/api/library/chapters', methods=['GET'])
def get_chapters():
    """Get all chapters"""
    try:
        chapters = library.get_all_chapters()
        return jsonify({
            'success': True,
            'chapters': chapters,
            'total': len(chapters)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/library/chapter/<chapter_id>', methods=['GET'])
def get_chapter(chapter_id):
    """Get a specific chapter"""
    try:
        chapter = library.get_chapter(chapter_id)
        if not chapter:
            return jsonify({'error': 'Chapter not found'}), 404

        progress = library.get_progress(chapter_id)

        return jsonify({
            'success': True,
            'chapter': chapter,
            'progress': progress
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/library/chapter', methods=['POST'])
def add_chapter():
    """Add a new chapter to the library"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        content = data.get('text', '').strip()
        voice_name = data.get('voice', 'alloy')
        speed = float(data.get('speed', 1.0))

        if not title:
            return jsonify({'error': 'No title provided'}), 400
        if not content:
            return jsonify({'error': 'No content provided'}), 400

        # Get voice
        voice = VOICES.get(voice_name, Voice.ALLOY)

        # Generate chapter ID
        chapter_id = f"chapter_{uuid.uuid4().hex[:12]}"

        # Check text length
        text_length = len(content)

        if text_length > 1000:
            # Use long text method with auto-combine
            print(f"Processing long chapter ({text_length} characters) with auto-combine...")
            response = tts_client.generate_speech_long_text(
                text=content,
                voice=voice,
                response_format=AudioFormat.MP3,
                speed=speed,
                max_length=1000,
                preserve_words=True,
                auto_combine=True
            )
        else:
            # Use regular method for short text
            response = tts_client.generate_speech(
                text=content,
                voice=voice,
                response_format=AudioFormat.MP3,
                speed=speed,
                validate_length=False
            )

        # Generate filename
        filename_base = f"{chapter_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        filepath_base = os.path.join(app.config['OUTPUT_FOLDER'], filename_base)

        # Save audio file
        response.save_to_file(filepath_base)

        # Get actual filename with extension
        actual_extension = response.format.value
        actual_filename = f"{filename_base}.{actual_extension}"

        # Add to library
        chapter_data = library.add_chapter(
            chapter_id=chapter_id,
            title=title,
            content=content,
            audio_filename=actual_filename
        )

        return jsonify({
            'success': True,
            'chapter': chapter_data,
            'message': f'Chapter added successfully ({text_length} characters)'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/library/chapter/<chapter_id>', methods=['DELETE'])
def delete_chapter(chapter_id):
    """Delete a chapter"""
    try:
        audio_filename = library.delete_chapter(chapter_id)

        if audio_filename:
            # Delete audio file
            audio_path = os.path.join(app.config['OUTPUT_FOLDER'], audio_filename)
            if os.path.exists(audio_path):
                os.remove(audio_path)

            return jsonify({
                'success': True,
                'message': 'Chapter deleted successfully'
            })
        else:
            return jsonify({'error': 'Chapter not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/library/progress/<chapter_id>', methods=['POST'])
def update_progress(chapter_id):
    """Update reading progress"""
    try:
        data = request.get_json()
        current_time = float(data.get('current_time', 0))

        library.update_progress(chapter_id, current_time)

        return jsonify({
            'success': True,
            'message': 'Progress updated'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting TTSFM Web Application...")
    print("Open your browser and navigate to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

