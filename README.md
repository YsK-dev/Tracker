# Job Application Tracker

A Streamlit-based application that automatically analyzes your job application emails using AI to track responses, categorize feedback, and provide insights into your job search progress.

## Features

- **Email Integration**: Connects to your Gmail account via IMAP to fetch recent emails
- **AI-Powered Analysis**: Uses OpenRouter API with Mistral AI to categorize and summarize job application responses
- **Smart Categorization**: Automatically classifies emails as Positive, Negative, Neutral, or Follow-up needed
- **Visual Analytics**: Interactive charts and graphs showing your application progress
- **Timeline Tracking**: Daily trends of email responses over time
- **Export Functionality**: Download your email data as CSV for further analysis
- **Batch Processing**: Efficient processing of multiple emails for better performance

## Prerequisites

1. **Gmail Account** with 2-Factor Authentication enabled
2. **OpenRouter Account** with API credits
3. **Python 3.7+** installed on your system

## Setup Instructions

### 1. Gmail Configuration

1. Enable 2-factor authentication on your Google account
2. Go to [Google Account Settings](https://myaccount.google.com/)
3. Navigate to **Security > 2-Step Verification > App passwords**
4. Generate a new app password for 'Mail'
5. Save this 16-character password (you'll need it for the environment variables)

### 2. OpenRouter Setup

1. Sign up at [OpenRouter](https://openrouter.ai/)
2. Get your API key from the dashboard
3. Add credits to your account if needed

### 3. Environment Configuration

Create a `.env` file in the project directory with the following variables:

```env
EMAIL=your@gmail.com
EMAIL_PASSWORD=your_16_digit_app_password
OPENROUTER_API_KEY=your_openrouter_api_key
```

**Important**: For the Gmail app password, remove all spaces. For example, if your app password is "uzb noxp zlgs phfm", use "uzbnoxpzlgshphfm".

### 4. Installation

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install streamlit pandas plotly requests python-dotenv
```

## Usage

### Running the Application

```bash
streamlit run main.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Features Overview

#### Dashboard
- **Email Summary**: Total count of processed emails
- **Category Breakdown**: Pie chart and bar chart showing response types
- **Daily Trends**: Timeline showing email activity over the past 7 days

#### Email Analysis
- **Automatic Categorization**: AI classifies emails into four categories:
  - **Positive**: Interview invitations, next steps, congratulations
  - **Negative**: Rejections, "not selected" responses
  - **Follow-up needed**: Requests for documents, confirmations
  - **Neutral**: General acknowledgments, automated responses

#### Data Export
- Download processed email data as CSV for external analysis
- Includes sender, subject, date, category, summary, and suggested actions

## Technical Details

### Architecture
- **Frontend**: Streamlit web interface
- **Email Processing**: Python's `imaplib` for IMAP connection
- **AI Integration**: OpenRouter API with Mistral-7B-Instruct model
- **Data Visualization**: Plotly for interactive charts
- **Data Handling**: Pandas for data manipulation

### Performance Features
- **Connection Management**: Automatic reconnection handling for long-running operations
- **Batch Processing**: Multiple emails processed in single API calls
- **Error Handling**: Graceful fallback to rule-based classification
- **Rate Limiting**: Controlled email fetching to prevent server overload

### Security
- Environment variable configuration for sensitive data
- Support for Streamlit Cloud secrets
- No storage of email credentials in code

## Troubleshooting

### Common Issues

1. **"Application-specific password required"**
   - Ensure 2FA is enabled on your Google account
   - Use the 16-character app password, not your regular Gmail password

2. **"Connection timeout"**
   - Check your internet connection
   - Verify Gmail IMAP is enabled in your account settings

3. **"No emails found"**
   - The app looks for emails from the last 7 days
   - Ensure you have job-related emails in that timeframe

4. **OpenRouter API errors**
   - Verify your API key is correct
   - Check that you have sufficient credits in your OpenRouter account

### Configuration for Streamlit Cloud

If deploying to Streamlit Cloud, add these secrets in your app settings:

```toml
[secrets]
EMAIL = "your@gmail.com"
EMAIL_PASSWORD = "your_16_digit_app_password"
OPENROUTER_API_KEY = "your_openrouter_api_key"
```

## File Structure

```
Tracker/
├── main.py              # Main application file
├── .env                 # Environment variables (create this)
├── README.md           # This file
└── requirements.txt    # Python dependencies (optional)
```

## Dependencies

- `streamlit`: Web application framework
- `pandas`: Data manipulation and analysis
- `plotly`: Interactive data visualization
- `requests`: HTTP library for API calls
- `python-dotenv`: Environment variable management
- `imaplib`: Built-in Python IMAP client
- `email`: Built-in Python email parsing

## Contributing

This is a personal project, but suggestions and improvements are welcome. Feel free to:
- Report bugs or issues
- Suggest new features
- Propose code improvements

## License

This project is for personal use. Please ensure compliance with Gmail's Terms of Service and OpenRouter's usage policies when using this application.

## Limitations

- Currently supports Gmail only (IMAP)
- Processes last 7 days of emails only
- Limited to 30 most recent emails for performance
- Requires active internet connection
- Dependent on OpenRouter API availability

## Future Enhancements

- Support for other email providers
- Extended date range options
- Email template generation for follow-ups
- Integration with job boards and applicant tracking systems
- Advanced analytics and reporting features
