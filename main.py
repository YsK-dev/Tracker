import os
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
from dotenv import load_dotenv
import time
import re
import socket

# Load environment variables
load_dotenv()

# Configuration - try Streamlit secrets first, then fall back to environment variables
try:
    EMAIL = st.secrets["EMAIL"]
    PASSWORD = st.secrets["EMAIL_PASSWORD"]
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
except:
    # Fallback to environment variables for local development
    EMAIL = os.getenv('EMAIL')
    PASSWORD = os.getenv('EMAIL_PASSWORD')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

IMAP_SERVER = 'imap.gmail.com'

# OpenRouter configuration
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "mistralai/mistral-7b-instruct"

def connect_email():
    """Connect to IMAP server and return mailbox"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=30)
        # Remove spaces from password
        cleaned_password = PASSWORD.replace(" ", "")
        mail.login(EMAIL, cleaned_password)
        st.success("Successfully connected to email server")
        return mail
    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        if 'Application-specific password' in error_msg:
            st.error("""
            Gmail requires an application-specific password for IMAP access.
            
            Steps to fix this:
            1. Enable 2-factor authentication on your Google account
            2. Go to your Google Account settings (https://myaccount.google.com/)
            3. Navigate to Security > 2-Step Verification > App passwords
            4. Generate a new app password for 'Mail'
            5. Use this 16-character password in your .env file as EMAIL_PASSWORD
            """)
        else:
            st.error(f"IMAP connection error: {error_msg}")
        return None
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

def fetch_emails(mail, days=7):
    """Fetch emails from last N days with retry logic"""
    try:
        since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        mail.select('inbox')
        
        # Search for emails from the last 7 days, sorted by date (newest first)
        status, messages = mail.search(None, f'(SINCE "{since_date}")')
        
        if status != 'OK':
            st.error("No emails found")
            return []
        
        email_ids = messages[0].split()
        
        # Reverse the list to get newest emails first
        email_ids.reverse()
        
        # Only process a limited number of emails for performance
        max_emails = min(30, len(email_ids))  # Increased to 30 emails
        email_ids = email_ids[:max_emails]  # Take the newest emails
        
        emails = []
        
        for i, email_id in enumerate(email_ids):
            try:
                # Check connection periodically and reconnect if needed
                if i % 10 == 0:
                    try:
                        mail.noop()  # Keep connection alive
                    except:
                        st.warning("Connection lost, reconnecting...")
                        mail = connect_email()
                        if not mail:
                            return emails
                        mail.select('inbox')
                
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                    
                msg = email.message_from_bytes(msg_data[0][1])
                subject, encoding = decode_header(msg['Subject'])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or 'utf-8')
                
                from_ = msg.get('From')
                date_ = msg.get('Date')
                
                # Get email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode(errors='ignore')
                            except:
                                body = part.get_payload()
                            break
                else:
                    try:
                        body = msg.get_payload(decode=True).decode(errors='ignore')
                    except:
                        body = msg.get_payload()
                
                # Clean up body text
                body = re.sub(r'\s+', ' ', body).strip()
                
                # Extract sender name from email address
                from_name = from_
                match = re.search(r'([^<]+)<', from_)
                if match:
                    from_name = match.group(1).strip()
                
                emails.append({
                    'from': from_name,
                    'subject': subject,
                    'date': date_,
                    'body': body
                })
                
            except (socket.error, imaplib.IMAP4.error) as e:
                st.warning(f"Connection error, attempting to reconnect: {str(e)}")
                try:
                    mail.logout()
                except:
                    pass
                mail = connect_email()
                if not mail:
                    return emails
                mail.select('inbox')
                continue
            except Exception as e:
                st.warning(f"Error processing email: {str(e)}")
                continue
        
        return emails
    except Exception as e:
        st.error(f"Error fetching emails: {str(e)}")
        return []

def process_emails_batch(emails):
    """Process multiple emails in a single API call"""
    if not emails:
        return []
    
    # Create a batch prompt
    batch_prompt = "Classify and summarize these job application emails:\n\n"
    
    for i, email_data in enumerate(emails):
        batch_prompt += f"Email {i+1}:\n"
        batch_prompt += f"Subject: {email_data['subject']}\n"
        batch_prompt += f"Body: {email_data['body'][:300]}\n\n"
    
    batch_prompt += """
    For each email, provide:
    1. Category (Positive, Negative, Neutral, or Follow-up needed)
    2. A brief summary (1-2 sentences)
    
    Format your response as:
    Email 1: Category: <category>, Summary: <summary>
    Email 2: Category: <category>, Summary: <summary>
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": batch_prompt}],
            "max_tokens": 800,
            "temperature": 0.1
        }
        
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        response_text = result['choices'][0]['message']['content'].strip()
        
        # Parse the response
        processed_emails = []
        lines = response_text.split('\n')
        
        for i, line in enumerate(lines):
            if f"Email {i+1}:" in line:
                category_match = re.search(r'Category:\s*(\w+(?:\s+\w+)*)', line, re.IGNORECASE)
                summary_match = re.search(r'Summary:\s*(.*)', line, re.IGNORECASE)
                
                category = "Neutral"  # Default
                summary = "No summary available"
                
                if category_match:
                    category_text = category_match.group(1).lower()
                    if "positive" in category_text:
                        category = "Positive"
                    elif "negative" in category_text:
                        category = "Negative"
                    elif "follow" in category_text or "needed" in category_text:
                        category = "Follow-up needed"
                
                if summary_match:
                    summary = summary_match.group(1).strip()
                
                processed_emails.append({
                    'category': category,
                    'summary': summary
                })
        
        return processed_emails
        
    except Exception as e:
        st.warning(f"Batch processing error: {str(e)}")
        # Fallback: process individually
        return process_emails_individually(emails)

def process_emails_individually(emails):
    """Process emails one by one (fallback method)"""
    results = []
    
    for email_data in emails:
        # Simple rule-based classification as fallback
        subject_lower = email_data['subject'].lower()
        body_lower = email_data['body'].lower()
        
        # Simple classification rules
        if any(word in subject_lower + body_lower for word in ['interview', 'next step', 'schedule', 'congratulation']):
            category = "Positive"
        elif any(word in subject_lower + body_lower for word in ['reject', 'not selected', 'unfortunately', 'regret']):
            category = "Negative"
        elif any(word in subject_lower + body_lower for word in ['follow up', 'document', 'confirm', 'required']):
            category = "Follow-up needed"
        else:
            category = "Neutral"
        
        # Simple summary extraction
        sentences = re.split(r'[.!?]+', email_data['body'])
        summary = sentences[0][:150] + "..." if len(sentences[0]) > 150 else sentences[0]
        
        results.append({
            'category': category,
            'summary': summary
        })
    
    return results

def generate_summary(df):
    """Generate weekly summary report"""
    summary = {
        'Positive': len(df[df['Category'] == 'Positive']),
        'Negative': len(df[df['Category'] == 'Negative']),
        'Neutral': len(df[df['Category'] == 'Neutral']),
        'Follow-up needed': len(df[df['Category'] == 'Follow-up needed'])
    }
    return summary

def create_timeline(df):
    """Create timeline of email responses"""
    try:
        # Try to parse dates with different formats
        df['date_parsed'] = pd.to_datetime(df['Date'], errors='coerce', utc=True)
        df = df.dropna(subset=['date_parsed'])
        df['date_only'] = df['date_parsed'].dt.date
        daily_counts = df.groupby(['date_only', 'Category']).size().unstack(fill_value=0)
        return daily_counts
    except Exception as e:
        st.warning(f"Could not create timeline: {str(e)}")
        return pd.DataFrame()

def main():
    st.title("Job Application Tracker")
    
    # Display setup instructions
    with st.expander("Setup Instructions"):
        st.markdown("""
        ### Email Setup (Gmail)
        1. Enable 2-factor authentication on your Google account
        2. Go to your Google Account settings (https://myaccount.google.com/)
        3. Navigate to Security > 2-Step Verification > App passwords
        4. Generate a new app password for 'Mail'
        5. Use this 16-character password in your .env file as EMAIL_PASSWORD
        
        ### OpenRouter Setup
        1. Sign up at https://openrouter.ai/
        2. Get your API key from the dashboard
        3. Add credits to your account if needed
        
        ### Environment Variables
        Create a `.env` file in the same directory with:
        ```
        EMAIL=your@gmail.com
        EMAIL_PASSWORD=your_16_digit_app_password
        OPENROUTER_API_KEY=your_openrouter_api_key
        ```
        
        For your app password "uzb noxp zlgs phfm", remove the spaces and use "uzbnoxpzlgshphfm"
        """)
    
    # Check if environment variables are set
    if not EMAIL:
        st.error("EMAIL environment variable is not set")
    if not PASSWORD:
        st.error("EMAIL_PASSWORD environment variable is not set")
    if not OPENROUTER_API_KEY:
        st.error("OPENROUTER_API_KEY environment variable is not set")
    
    if not all([EMAIL, PASSWORD, OPENROUTER_API_KEY]):
        st.error("Missing environment variables. Please check the setup instructions above.")
        return

    with st.spinner("Connecting to email server..."):
        mail = connect_email()
        if not mail:
            return
        
        emails = fetch_emails(mail)
        if mail:
            try:
                mail.logout()
            except:
                pass

    if not emails:
        st.warning("No emails found in the last 7 days")
        return

    # Process emails in batches for better performance
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("Processing emails...")
    processed_results = process_emails_batch(emails)
    
    # If batch processing failed, fall back to individual processing
    if len(processed_results) != len(emails):
        status_text.text("Using fallback processing...")
        processed_results = process_emails_individually(emails)
    
    # Combine results
    data = []
    for i, (email_data, result) in enumerate(zip(emails, processed_results)):
        data.append({
            'From': email_data['from'],
            'Subject': email_data['subject'],
            'Date': email_data['date'],
            'Category': result['category'],
            'Summary': result['summary'],
            'Suggested Action': 'Follow up' if result['category'] == 'Follow-up needed' else 'Monitor'
        })
        progress_bar.progress((i + 1) / len(emails))
    
    status_text.empty()
    progress_bar.empty()
    
    if not data:
        st.warning("No emails were successfully processed")
        return
        
    df = pd.DataFrame(data)
    
    # Display total email count
    st.subheader(f"Email Summary - Total: {len(df)} emails")
    
    summary = generate_summary(df)
    timeline = create_timeline(df)

    # Display results
    st.subheader("Weekly Summary")
    col1, col2 = st.columns(2)
    
    with col1:
        if any(summary.values()):
            fig = px.pie(values=list(summary.values()), names=list(summary.keys()), 
                         title="Response Categories")
            st.plotly_chart(fig)
        else:
            st.info("No data available for chart")
    
    with col2:
        if any(summary.values()):
            fig = px.bar(x=list(summary.keys()), y=list(summary.values()), 
                         title="Response Counts", labels={'x': 'Category', 'y': 'Count'})
            st.plotly_chart(fig)
        else:
            st.info("No data available for chart")

    st.subheader("Daily Trends")
    if not timeline.empty:
        fig = px.line(timeline, title="Emails Over Time")
        st.plotly_chart(fig)
    else:
        st.info("No timeline data available")

    st.subheader("Email Details")
    # Use a container to make the email details section larger
    with st.container():
        # Add a summary of categories
        st.markdown("### Category Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Positive", summary['Positive'])
        with col2:
            st.metric("Negative", summary['Negative'])
        with col3:
            st.metric("Neutral", summary['Neutral'])
        with col4:
            st.metric("Follow-up", summary['Follow-up needed'])
        
        # Display the dataframe with full width and height
        st.dataframe(
            df, 
            use_container_width=True,
            height=min(600, 35 * len(df) + 38)  # Dynamic height based on number of rows
        )
        
        # Add download button for the data
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Email Data as CSV",
            data=csv,
            file_name="job_application_emails.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()