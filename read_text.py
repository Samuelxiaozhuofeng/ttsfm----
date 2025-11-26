"""
Script to read text.md file using TTSFM
"""
from ttsfm import TTSClient, Voice, AudioFormat

def read_text_file():
    # Read the text from text.md
    with open("text.md", "r", encoding="utf-8") as f:
        text = f.read()
    
    print("Reading text.md file...")
    print(f"Text length: {len(text)} characters")
    
    # Create TTSFM client
    client = TTSClient()
    
    # Generate speech - disable length validation for long text
    print("Generating speech...")
    response = client.generate_speech(
        text=text,
        voice=Voice.ALLOY,
        response_format=AudioFormat.MP3,
        speed=1.0,
        validate_length=False  # Disable length validation for long text
    )

    # Save to file
    output_file = "text_output.mp3"
    response.save_to_file(output_file)
    print(f"Speech saved to {output_file}")
    print("Done!")

if __name__ == "__main__":
    read_text_file()

