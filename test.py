from client import MeetingSummarizerClient
import os
import json
from pathlib import Path

client = MeetingSummarizerClient("http://54.202.125.206:5001")

# Create results directory if it doesn't exist
results_dir = "test_results"
os.makedirs(results_dir, exist_ok=True)

# Get all transcript files from transcripts_split folder
transcripts_folder = "transcripts_split"
transcript_files = sorted([f for f in os.listdir(transcripts_folder) if f.endswith(".txt")])

print(f"Found {len(transcript_files)} transcripts to analyze...\n")

results_summary = []

# Process each transcript
for transcript_file in transcript_files:
    transcript_path = os.path.join(transcripts_folder, transcript_file)
    
    # Read the transcript
    with open(transcript_path, "r") as f:
        transcript_content = f.read()
    
    print(f"Analyzing {transcript_file}...")
    
    try:
        # Analyze the transcript
        result = client.analyze(
            transcript=transcript_content,
            meeting_info={
                "title": f"Meeting from {transcript_file}",
                "date": "2025-10-30",
                "time": "2:00 PM"
            }
        )
        
        # Save individual result
        result_filename = transcript_file.replace(".txt", "_result.json")
        result_path = os.path.join(results_dir, result_filename)
        
        with open(result_path, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"  ✓ Saved to {result_path}")
        
        # Add to summary
        results_summary.append({
            "transcript": transcript_file,
            "status": "success",
            "result": result
        })
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        results_summary.append({
            "transcript": transcript_file,
            "status": "error",
            "error": str(e)
        })

# Save overall summary
summary_path = os.path.join(results_dir, "summary.json")
with open(summary_path, "w") as f:
    json.dump(results_summary, f, indent=2)

print(f"\n✅ All transcripts processed! Results saved to {results_dir}/")
print(f"Summary saved to {summary_path}")