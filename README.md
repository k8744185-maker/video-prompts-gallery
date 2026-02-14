# 🎬 Video Prompts Gallery

A simple web application to store and share AI video generation prompts.

## Features
- 📝 Add video generation prompts
- 📚 View all saved prompts
- 💾 Store in Google Sheets
- 🔗 Easy to share via link

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure `.env` file:
```env
GOOGLE_CREDENTIALS_PATH=./credentials.json
GOOGLE_SHEET_ID=your-google-sheet-id
```

3. Run the app:
```bash
streamlit run app.py
```

## Usage

1. Share your website link on Instagram
2. Users can view all your video prompts
3. You can add new prompts anytime

## Google Sheets Setup

Create a new Google Sheet with these columns:
- Timestamp
- Prompt
- Video ID
